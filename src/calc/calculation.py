from calc.data import assertCount
from calc.cells import Cell, shortcutCells
from calc.params import Param, shortcutParams
from calc.species import shortcutSpecies

from itertools import product


stringShortcuts = shortcutCells | shortcutParams | shortcutSpecies

def getShortcut(arg=None):
    assert type(arg) is str

    shortcutList = stringShortcuts.get(arg.lower(), None)

    if shortcutList is None:
        raise ValueError('Shortcut {} not found'.format(arg))

    return shortcutList


def parseArgs(*args):
    if len(args) == 0:
        return [], [], []

    cells = []
    params = []
    strings = []

    for arg in args:
        t = type(arg)

        if t is str:
            strings.append(arg)

        elif t is Cell:
            cells.append(arg)

        elif t is Param:
            params.append(arg)

        elif t is tuple:
            for arg2 in arg:
                t2 = type(arg2)

                if t2 is str:
                    strings.append(arg2)

                elif t2 is Cell:
                    cells.append(arg2)

                elif t2 is Param:
                    params.append(arg2)

                else:
                    raise TypeError('Cannot have type {} in tuple'.format(t2))

        elif t is list:
            for arg2 in arg:
                t2 = type(arg2)

                if t2 is str:
                    strings.append(arg2)

                elif t2 is Cell:
                    cells.append(arg2)

                elif t2 is Param:
                    params.append(arg2)

                else:
                    raise TypeError('Cannot have type {} in list'.format(t2))

        else:
            raise TypeError('Cannot have type {}'.format(t))

    return cells, params, strings


def translateStrings(strings=None):
    assert type(strings) in [tuple, list]

    if len(strings) == 0:
        return [], []

    cells = []
    params = []

    for string in strings:
        newCells, newParams = stringShortcuts.get(string.lower(), (None, None))

        assert newCells is not None and newParams is not None, 'Shortcut string {} not recognised'.format(string)

        cells += newCells
        params += newParams

    return cells, params


def setupCalculations(*args, other=None):
    cellsGeneral = []
    paramsGeneral = []

    # Check if there are any general cells or params defined.
    if other is not None:
        other = [other] if type(other) is str else other

        assert type(other) in [list, tuple]
        cellsGeneral, paramsGeneral, strings = parseArgs(*other)

        # Check that we have one of each string.
        assertCount([string.lower() for string in strings])

        # The strings are shortcuts to one or more params/cells.
        # "Translate" from the string to these shortcuts and get them.
        # E.g. 'soc' is spin_treatment=vector and spin_orbit_coupling=true.
        cellsFromStrings, paramsFromStrings = translateStrings(strings)

        # Add the shortcut cells/params.
        cellsGeneral += cellsFromStrings
        paramsGeneral += paramsFromStrings

        # Check that none of the shortcuts themselves have now duplicated any cells/params.
        assertCount([cell.key for cell in cellsGeneral])
        assertCount([param.key for param in paramsGeneral])

    # Now that we have dealt with the general cells/params of the calculations, we now work on the variable cells/params.

    arguments = []
    numbering = []

    # Loop through the different combinations.
    for arg in args:
        assert type(arg) in [str, list],\
            'Specify only shortcut strings or lists for variable cells/params, not {}'.format(type(arg))

        # Strings are shortcuts, but shortcuts to specific combinations of cells/params.
        # E.g. 'soc' is a tuple of three different settings:
        # 1 -> spin_treatment=scalar and spin_orbit_coupling=false
        # 2 -> spin_treatment=vector and spin_orbit_coupling=false
        # 3 -> spin_treatment=vector and spin_orbit_coupling=true
        # So let's just put the string in a list so we can treat it the same as the rest.
        arg = [arg] if type(arg) is str else arg

        # Create a list to store this combination.
        lst = []

        for strListCellParam in arg:
            type_ = type(strListCellParam)

            # Shortcut string.
            if type_ is str:
                shortcut = getShortcut(strListCellParam)
                lst.append(shortcut)

            # User defined.
            elif type_ in [list, tuple]:
                assert all(type(s) in [Cell, Param] for s in strListCellParam), 'Settings should only be cells or params'
                lst.append(list(strListCellParam))

            elif type_ in [Cell, Param]:
                lst.append([strListCellParam])

            else:
                raise TypeError('A specific setting of several cells/params must be given as a shortcut or tuple')

        arguments.append(lst)
        numbering.append(list(range(1, len(arg)+1)))

    #assert sum(any(type(a) is str for a in arg) for arg in arguments) == 1,\
    #    'Can only have one iterable argument that is not a cell or param'

    # arguments looks like = [argument1, argument2, etc...]   ~ this is all the information
    # argumentI looks like = [sett1, sett2, sett3, etc...]    ~ each argument will be a directory
    # settI     looks like = [param1, param2, cell1, etc...]  ~ each setting has specific cells/params for that directory

    # Combinations will expand out the arguments and create every possible combination of the variable settings.
    # E.g. If we have argument1=['HF', 'HCl'] and argument2=[Cell(bField=1.0T), Cell(bField=2.0T)]
    # Then combinations will be: [(HF, bField 1.0T), (HF, bField 2.0T), (HCl, bField 1.0T), (HCl, bField 2.0T)]
    combinations = list(product(*arguments))
    numbering = list(product(*numbering))

    calculations = []

    # Loop through the possible combinations.
    for combNum, combination in enumerate(combinations):
        nums = numbering[combNum]
        name = None

        directory = '' # '{}'.format(get current working directory)

        # For the specific variable cells/params.
        cellsSpecific = []
        paramsSpecific = []

        # Loop through the tuples of specific cells/params of this combination.
        for settNum, setting in enumerate(combination):
            n = nums[settNum]

            directory += '{:03}'.format(n)

            # Loop through the specific tuple that contains many cells or params or both.
            for cellOrParam in setting:
                if type(cellOrParam) is Cell:
                    cellsSpecific.append(cellOrParam)
                    directory += '_{}'.format(cellOrParam.lines)

                elif type(cellOrParam) is Param:
                    paramsSpecific.append(cellOrParam)
                    directory += '_{}'.format(str(cellOrParam.value).lower())

                else:
                    raise TypeError('Only cells/params define a calculation, not {}'.format(type(cellOrParam)))

            directory += '/'

            '''
            if type(setting) is str:
                name = setting
                directory += '{:03}_{}/'.format(n, name)
            '''

        # Combine the general cells/params we want with the variable cells/params.
        cells = cellsGeneral + cellsSpecific
        params = paramsGeneral + paramsSpecific

        # Create the calculation.
        calculations.append(Calculation(name=name,
                                        directory=directory,
                                        cells=cells,
                                        params=params))

    return calculations



class Calculation:
    name = None
    directory = None
    cells = None
    params = None

    def __init__(self, name=None, directory=None,
                 cells=None, params=None):
        if name is not None:
            assert type(name) is str

        self.name = name

        if directory is not None:
            assert type(directory) is str

        self.directory = directory

        if cells is not None:
            assert type(cells) is list
            assert all(type(cell) == Cell for cell in cells)

        if params is not None:
            assert type(params) is list
            assert all(type(param) == Param for param in params)

        self.cells = cells
        self.params = params

    def __str__(self):
        string = 'Calculation ->'

        if self.name is not None:
            string += ' {}'.format(self.name)

        if self.directory is not None:
            string += ' ({})'.format(self.directory)

        if self.params is None and self.cells is None:
            string += '\n  *** empty ***'
            return string

        spaces = 20

        if self.cells is not None:
            string += '\n'

            for cell in self.cells:
                string += '  {key:>{spaces}} : {lines:<{spaces}}\n'.format(key=cell.key,
                                                                           spaces=spaces,
                                                                           lines=', '.join(cell.lines))

        if self.params is not None:
            string += '\n'

            for param in self.params:
                string += '  {key:>{spaces}} : {value:<{spaces}}\n'.format(key=param.key,
                                                                           spaces=spaces,
                                                                           value=param.value)

        return string
