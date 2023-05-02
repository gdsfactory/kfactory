def clean_name(name: str, remove_dots: bool = False) -> str:
    """Return a string with correct characters for a cell name.

    [a-zA-Z0-9]

    FIXME: only a few characters are currently replaced.
        This function has been updated only on case-by-case basis

    """
    replace_map = {
        " ": "_",
        "!": "",
        "?": "",
        "#": "_",
        "%": "_",
        "(": "",
        ")": "",
        "*": "_",
        ",": "_",
        "-": "m",
        ".": "p",
        "/": "_",
        ":": "_",
        "=": "",
        "@": "_",
        "[": "",
        "]": "",
        "{": "",
        "}": "",
        "$": "",
    }

    if remove_dots:
        replace_map["."] = ""
    for k, v in list(replace_map.items()):
        name = name.replace(k, v)
    return name
