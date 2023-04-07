from jumanji.environments.routing.connector.generator import Generator
from jumanji.environments.routing.connector.env import Connector
from jumanji.environments.routing.connector.utils import get_position, get_target
from jumanji.environments.routing.connector.types import State, Agent
from jumanji.wrappers import AutoResetWrapper
from jumanji.registration import register
from jumanji import make
import chex

import jax
import jax.numpy as np

import kfactory as kf

c = kf.KCell()
obst1 = c << kf.pcells.waveguide.waveguide(1, 100, 0)
obst2 = c << kf.pcells.waveguide.waveguide(1, 100, 0)

obst1.transform(kf.kdb.Trans(0, False, 0, 50 / c.klib.dbu))
obst2.transform(kf.kdb.Trans(0, False, 50 / c.klib.dbu, 0))
# obst3 = c << kf.pcells.waveguide(10, 10, 0)
# obst3.transform(kf.kdb.Trans(0, False, 60 / c.klib.dbu, 30 / c.klib.dbu))

c.create_port(name="o1", trans=kf.kdb.Trans(0, False, 0, 0), width=1000, layer=0)
c.ports["o1"].center = (0 / c.klib.dbu, 0)
c.create_port(name="o2", trans=kf.kdb.Trans(3, False, 0, 0), width=1000, layer=0)
c.ports["o2"].center = (150 / c.klib.dbu, 50 / c.klib.dbu)
c.show()

class Grid(Generator):
    def __init__(self, c: kf.KCell, ports1: list[kf.Port], ports2: list[kf.Port]):
        self.ports1 = ports1
        self.ports2 = ports2
        c_ = kf.KCell()
        inst = c_ << c
        inst.transform(kf.kdb.DTrans(0, False, 0, -c.dbbox().height() + 0.5))
        c_.add_ports(inst.ports)
        c = c.transform_into(kf.kdb.DTrans(0, False, -c.dbbox().center().x, -c.dbbox().center().y))
        print(c_.bbox())
        self.c = c_
        grid_size = max(c.dbbox().width(), c.dbbox().height())
        grid_size = int(grid_size)
        num_agents = len(ports1)

        super().__init__(grid_size, num_agents)

    def __call__(self, key: chex.PRNGKey) -> State:
        """Generates a `Connector` state that contains the grid and the agents' layout.

        Returns:
            A `Connector` state.
        """
        key, pos_key = jax.random.split(key)
        starts_flat = np.array([], dtype=np.int32)
        for port in self.ports1:
            starts_flat = np.append(starts_flat, int(port.position[0] * port.position[1] * self.c.klib.dbu * self.c.klib.dbu - self.c.dbbox().p1.y))
        targets_flat = np.array([], dtype=np.int32)
        for port in self.ports2:
            print(port.position, self.grid_size, self.c.ports["o2"])
            targets_flat = np.append(targets_flat, int(port.position[0] * port.position[1] * self.c.klib.dbu * self.c.klib.dbu + self.c.dbbox().p1.y))

        # Create 2D points from the flat arrays.
        starts = np.divmod(starts_flat, self.grid_size)[::-1]
        targets = np.divmod(targets_flat, self.grid_size)
        # starts = (starts[0].astype(np.int32), starts[1].astype(np.int32))
        # targets = (targets[0].astype(np.int32), targets[1].astype(np.int32))
        print(starts, targets)
        # Get the agent values for starts and positions.
        agent_position_values = jax.vmap(get_position)(np.arange(self.num_agents))
        agent_target_values = jax.vmap(get_target)(np.arange(self.num_agents))

        # Create empty grid.
        grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int32)

        # Place the agent values at starts and targets.
        grid = grid.at[starts].set(agent_position_values)
        grid = grid.at[targets].set(agent_target_values)

        def get_obst_values(obst_id: np.int32) -> np.int32:
            return 1 + 3 * obst_id

        agent_paths_values = jax.vmap(get_obst_values)(np.arange(self.num_agents))
        for layer in self.c.klib.layer_indices():
            for shape in self.c.shapes(layer):
                point_ = np.array([])
                for point in [shape.dbbox().p1, shape.dbbox().p2]:
                    np.append(point_, ([int(point.x), int(point.y)]))
                grid = grid.at[point_[0][0]:point_[1][0], point_[0][1]:point_[1][1]].set(agent_paths_values)

        # Create the agent pytree that corresponds to the grid.
        print(starts, targets)
        agents = jax.vmap(Agent)(
            id=np.arange(self.num_agents),
            start=np.stack(starts, axis=1),
            target=np.stack(targets, axis=1),
            position=np.stack(starts, axis=1),
        )

        step_count = np.array(0, np.int32)

        return State(key=key, grid=grid, step_count=step_count, agents=agents)
    
class AutoRouter(Connector):
    def __init__(self, c, ports1, ports2):
        super().__init__(Grid(c, ports1, ports2))

# register("AutoRouter-v0", ".:AutoRouter", c=c, ports1=[c.ports["o1"]], ports2=[c.ports["o2"]])

env = AutoRouter(c, [c.ports["o1"]], [c.ports["o2"]])
# env = Connector()
# env = AutoResetWrapper(env)     # Automatically reset the environment when an episode terminates
num_actions = env.action_spec().num_values

random_key = jax.random.PRNGKey(0)
key1, key2 = jax.random.split(random_key)

def step_fn(state, key):
  action = jax.random.randint(key=key, minval=0, maxval=num_actions, shape=(1,))
  new_state, timestep = env.step(state, action)
  return new_state, timestep

# def run_n_steps(state, key, n):
#   random_keys = jax.random.split(key, n)
#   state, rollout = jax.lax.scan(step_fn, state, random_keys)
#   return state, rollout

# # Instantiate a batch of environment states
keys = jax.random.split(key1)
state, timestep = env.reset(keys)
print(open("dsd.txt", "w").write(str(state.grid.tolist())))
env.render(state)

# # Collect a batch of rollouts
# keys = jax.random.split(key2, batch_size)
# state, rollout = jax.vmap(run_n_steps, in_axes=(0, 0, None))(state, keys, rollout_length)
state, rollout = step_fn(state, key2)
env.render(state)

# Shape and type of given rollout:
# TimeStep(step_type=(7, 5), reward=(7, 5), discount=(7, 5), observation=(7, 5, 6, 6, 5), extras=None)
