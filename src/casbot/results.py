from casbot.data import getElement, getIon,\
    getUnit, getFromDict,\
    PrintColors,\
    strListToArray

from numpy import ndarray


NMRresults = ['nmr_core', 'nmr_bare', 'nmr_dia', 'nmr_para', 'nmr_total']

EFGresults = ['efg_bare', 'efg_ion', 'efg_aug', 'efg_aug2', 'efg_total']

hyperfineResults = ['hyperfine_dipolarbare', 'hyperfine_dipolaraug', 'hyperfine_dipolaraug2', 'hyperfine_dipolar',
                    'hyperfine_fermi', 'hyperfine_zfc', 'hyperfine_total']

spinResults = ['spin_density']

forcesResults = ['forces']

resultKnown = NMRresults + EFGresults + hyperfineResults + spinResults + forcesResults

resultNames = {'nmr_core': 'CORE',
               'nmr_bare': 'BARE',
               'nmr_dia': 'DIA',
               'nmr_para': 'PARA',
               'nmr_total': 'TOTAL',

               'efg_bare': 'BARE',
               'efg_ion': 'ION',
               'efg_aug': 'AUG',
               'efg_aug2': 'AUG2',
               'efg_total': 'TOTAL',

               'hyperfine_dipolarbare': 'DIPOLAR BARE',
               'hyperfine_dipolaraug': 'DIPOLAR AUG',
               'hyperfine_dipolaraug2': 'DIPOLAR AUG2',
               'hyperfine_dipolar': 'DIPOLAR',
               'hyperfine_fermi': 'FERMI',
               'hyperfine_zfc': 'ZFC',
               'hyperfine_total': 'TOTAL',

               'spin_density': 'SPIN DENSITY',

               'forces': 'FORCES'}

resultWords = {'nmr_core': 'core',
               'nmr_bare': 'bare',
               'nmr_dia': 'dia',
               'nmr_para': 'para',
               'nmr_total': 'total',

               'efg_bare': 'bare',
               'efg_ion': 'ion',
               'efg_aug': 'aug',
               'efg_aug2': 'aug2',
               'efg_total': 'total',

               'hyperfine_dipolarbare': 'd_bare',
               'hyperfine_dipolaraug': 'd_aug',
               'hyperfine_dipolaraug2': 'd_aug2',
               'hyperfine_dipolar': 'dipolar',
               'hyperfine_fermi': 'fermi',
               'hyperfine_zfc': 'zfc',
               'hyperfine_total': 'total'}

resultUnits = { # TODO: NMR, EFG units

               'hyperfine_dipolarbare': 'energy',
               'hyperfine_dipolaraug': 'energy',
               'hyperfine_dipolaraug2': 'energy',
               'hyperfine_dipolar': 'energy',
               'hyperfine_fermi': 'energy',
               'hyperfine_zfc': 'energy',
               'hyperfine_total': 'energy',

               'spin_density': 'spin',

               'forces': 'force'}

resultColors = {'nmr_core': PrintColors.cyan,
                'nmr_bare': PrintColors.magenta,
                'nmr_dia': PrintColors.blue,
                'nmr_para': PrintColors.red,
                'nmr_total': PrintColors.orange,

                'efg_bare': PrintColors.red,
                'efg_ion': PrintColors.blue,
                'efg_aug': PrintColors.yellow,
                'efg_aug2': PrintColors.yellow,
                'efg_total': PrintColors.orange,

                'hyperfine_dipolarbare': PrintColors.blue,
                'hyperfine_dipolaraug': PrintColors.blue,
                'hyperfine_dipolaraug2': PrintColors.blue,
                'hyperfine_dipolar': PrintColors.blue,
                'hyperfine_fermi': PrintColors.green,
                'hyperfine_zfc': PrintColors.green,
                'hyperfine_total': PrintColors.orange}

assert set(resultNames).issubset(resultKnown)
assert set(resultWords).issubset(resultKnown)
assert set(resultUnits).issubset(resultKnown)
assert set(resultColors).issubset(resultKnown)


def getResult(resultToGet=None, lines=None):
    assert isinstance(resultToGet, str)
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)

    resultToGet = resultToGet.strip().lower()

    assert resultToGet in resultKnown

    if resultToGet in NMRresults:

        wordToLookFor = resultWords.get(resultToGet)

        tensors = []

        for num, line in enumerate(lines):
            parts = line.strip().lower().split()

            if len(parts) == 4:
                if parts[2] == wordToLookFor:
                    element = getElement(parts[0])

                    ion = getIon(parts[1])

                    arr = strListToArray(lines[num+2:num+5])

                    tensor = NMR(key=resultToGet, value=arr, unit=None, element=element, ion=ion)  # TODO: NMR units

                    tensors.append(tensor)

        return tensors

    elif resultToGet in EFGresults:

        wordToLookFor = resultWords.get(resultToGet)

        tensors = []

        for num, line in enumerate(lines):
            parts = line.strip().lower().split()

            if len(parts) == 4:
                if parts[2] == wordToLookFor and parts[3] == 'tensor':
                    element = getElement(parts[0])

                    ion = getIon(parts[1])

                    arr = strListToArray(lines[num+2:num+5])

                    tensor = NMR(key=resultToGet, value=arr, unit=None, element=element, ion=ion)  # TODO: EFG units

                    tensors.append(tensor)

        #if len(tensors) == 0:
        #    raise ValueError(f'Could not find any {resultToGet} tensors in results file')

        return tensors

    elif resultToGet in hyperfineResults:

        wordToLookFor = resultWords.get(resultToGet)

        tensors = []

        for num, line in enumerate(lines):
            parts = line.strip().lower().split()

            if len(parts) == 4:
                if parts[2] == wordToLookFor and parts[3] == 'tensor':
                    element = getElement(parts[0])

                    ion = getIon(parts[1])

                    arr = strListToArray(lines[num+2:num+5])

                    tensor = NMR(key=resultToGet, value=arr, unit='MHz', element=element, ion=ion)

                    tensors.append(tensor)

        #if len(tensors) == 0:
        #    raise ValueError(f'Could not find any {resultToGet} tensors in results file')

        return tensors


    elif resultToGet in spinResults:
        hits = []

        for num, line in enumerate(lines, 1):
            line = line.strip().lower()

            if 'integrated spin density' in line:
                parts = line.split('=')

                assert len(parts) == 2, f'Error in spin density on line {num} of results file'

                parts = parts[1].strip().split()

                assert len(parts) in (2, 4), f'Could not determine scalar or vector spin density on line {num} of results file'

                arr = strListToArray(parts[:-1])

                density = SpinDensity(key=resultToGet, value=arr, unit='hbar/2', shape=(len(parts)-1, 1))

                hits.append(density)

        #if len(hits) == 0:
        #    raise ValueError(f'Could not find any spin density values/vectors in result file')

        return None if len(hits) == 0 else hits[-1]


    elif resultToGet in forcesResults:
        # Groups are groups of forces: one group for each SCF cycle.
        # In each group, there will be n hits where n is the number of ions.
        groups = []

        for num, line in enumerate(lines):
            line = line.strip().lower()

            if '* forces *' in line and line.startswith('*') and line.endswith('*'):
                hits = []

                for numInBlock, lineInBlock in enumerate(lines[num:]):
                    lineInBlock = lineInBlock.strip()

                    if all(char == '*' for char in lineInBlock):
                        break
                    else:
                        parts = lineInBlock.split()

                        if len(parts) == 7:
                            element = getElement(parts[1])

                            ion = getIon(parts[2])

                            vector = strListToArray(parts[3:-1])

                            force = Force(key=resultToGet, value=vector, unit='eV/Ang', element=element, ion=ion)

                            hits.append(force)
                else:
                    raise ValueError('Cannot find end of forces block in results file')

                groups.append(hits)

        #if len(hits) == 0:
        #   raise ValueError(f'Could not find any force vectors in result file')

        return [] if len(groups) == 0 else groups[-1]


    else:
        raise ValueError(f'Do not know how to get result {resultToGet}')


class Result:
    def __init__(self, key=None):
        assert isinstance(key, str)

        key = key.strip().lower()

        assert key in resultKnown, f'{key} not a known result'

        self.key = key
        self.name = getFromDict(key=key, dct=resultNames, strict=True)


class Tensor(Result):
    def __init__(self, key=None, value=None, unit=None, shape=None):
        super().__init__(key=key)

        assert isinstance(value, ndarray), f'Value {value} not acceptable for {self.key}, should be {ndarray}'

        self.value = value
        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=resultUnits, strict=True)

        assert isinstance(shape, tuple)

        assert self.value.shape == shape, f'Tensor should be dimension {shape} not {self.value.shape}'

        self.shape = self.value.shape
        self.size = self.value.size

        self.trace = self.value.trace()

    def __str__(self):
        return '  '.join('{:>12.5E}' for _ in range(self.size)).format(*self.value.flatten())


class Vector(Result):
    def __init__(self, key=None, value=None, unit=None, shape=None):
        super().__init__(key=key)

        assert isinstance(value, ndarray), f'Value {value} not acceptable for {self.key}, should be {ndarray}'

        self.value = value
        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=resultUnits, strict=True)

        assert isinstance(shape, tuple)

        assert self.value.shape == shape, f'Array should be dimension {shape} not {self.value.shape}'

        self.shape = self.value.shape
        self.size = self.value.size

        self.norm = sum(v ** 2.0 for v in self.value) ** 0.5

    def __str__(self):
        return '   '.join('{:>12.5E}' for _ in range(self.size)).format(*self.value.flatten())


class NMR(Tensor):
    def __init__(self, key=None, value=None, unit=None, element=None, ion=None):
        super().__init__(key=key, value=value, unit=unit, shape=(3, 3))

        self.element = getElement(element)

        self.ion = getIon(ion)

        self.iso = self.trace / 3.0

        self.printColor = getFromDict(key=self.key, dct=resultColors, default='', strict=False)

    def __str__(self):
        rows = 3 * '\n        {:>12.5E}   {:>12.5E}   {:>12.5E}'

        return f'       |->   {self.element+self.ion:<3s} {self.printColor}{self.name:^16}{PrintColors.reset} {self.iso:>11.5f}   <-|{rows.format(*self.value.flatten())}'

    def __add__(self, other):
        assert self.key == other.key, 'Cannot add different NMR tensors'
        assert self.unit == other.unit, 'Cannot add tensors of different units'
        assert self.element == other.element, 'Cannot add tensors relating to different elements'
        assert self.ion == other.ion, 'Cannot add tensors relating to different ions'

        newValue = self.value + other.value

        return NMR(key=self.key,
                   value=newValue,
                   unit=self.unit,
                   element=self.element,
                   ion=self.ion)

    def __iadd__(self, other):
        self.__add__(other=other)

    def __sub__(self, other):
        assert self.key == other.key, 'Cannot sub different NMR tensors'
        assert self.unit == other.unit, 'Cannot sub tensors of different units'
        assert self.element == other.element, 'Cannot sub tensors relating to different elements'
        assert self.ion == other.ion, 'Cannot sub tensors relating to different ions'

        newValue = self.value - other.value

        return NMR(key=self.key,
                   value=newValue,
                   unit=self.unit,
                   element=self.element,
                   ion=self.ion)

    def __isub__(self, other):
        self.__sub__(other=other)

    def __eq__(self, other):
        return (self.value == other.value).all()


class SpinDensity(Vector):
    def __init__(self, key=None, value=None, unit=None, shape=None):
        super().__init__(key=key, value=value, unit=unit, shape=shape)


class Force(Vector):
    def __init__(self, key=None, value=None, unit=None, element=None, ion=None):
        super().__init__(key=key, value=value, unit=unit, shape=(3, 1))

        self.element = getElement(element)

        self.ion = getIon(ion)

    def __str__(self):
        Fx, Fy, Fz = self.value.flatten()

        return f'{self.element + self.ion:<3s}  {Fx:>12.5E}   {Fy:>12.5E}   {Fz:>12.5E}'
