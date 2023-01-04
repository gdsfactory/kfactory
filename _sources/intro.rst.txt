.. python(code):
   language: python

Getting Started
---------------

As an example we will build a small waveduide and instantiate a circular bend waveguide and connect them.

First let's create some layers. We will use the standard library for this.
Create a :file:`layers.py`. The full one can be downloaded here: :download:`layers.py`

Additionally we will create a :py:class:`~kfactory.utils.enclosure.Enclosure`. Enclosures allow to automatically generate claddings with minkosky sums or use a function to apply claddings to a cell or region. This enclosure will add the cladding to the bend we will use later.

.. literalinclude:: layers.py
   :language: python
   :linenos:

This will use the standard Library of KFactory.
A Library is the equivalent of a Layout object in KLayout and keeps track of the KCells.
It mirrors all the other functionalities of a Layout object.

Ports are created with the :py:func:`~kfactory.kcell.KCell.create_port` function. You can either specify a transformation as here or specify them in a similar manner to gdsfactory. See the API doc for more information.

Now, let's create a KCell for a waveguide. We will use the :py:func:`~kfactory.kcell.autocell`.
This will make sure that if we call the function multiple times that we don't create multiple cells in the layout.
Addiontally, compared to :py:func:`~kfactory.kcell.cell` it will also automatically name the cells using
the function name and the arguments and keyword arguments of the function.
In the end we will let KFactory take care of the naming of the ports we want to add.
This will allow them depending on the orientation of the port. This will sort the ports by orientation
(0,1,2,3 -> E,N,W,S) and by ascending x (N/S orientation) respectively y (E/W orientation) coordinates.

.. literalinclude:: waveguide.py
   :language: python
   :linenos:

The ``kf.show`` will create a GDS in the temp folder and then send the GDS by klive to KLayout (if klive is installed).
By running this with ``python waveguide.py``, this should show us a waveguide like this:

.. image:: _static/waveguide.png

Afterwards let's create the composite cell :download:`complex_cell.py`. This one instantiates a waveguide and a circular bend and then connects them.

.. literalinclude:: complex_cell.py
   :language: python
   :linenos:

With :py:func:`~kfactory.kcell.KCell.add_port` an existing port of an instance can be added to the parent cell. :py:func:`~kfactory.kcell.Instance.connect` allows an instance to be transformed so that one of its ports is connected to another port.

You will get a cell like this:

.. image:: _static/complex.png
