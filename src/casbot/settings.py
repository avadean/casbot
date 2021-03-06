from casbot.data import assertBetween, assertCount, \
    Any, elements, \
    getUnit, getFromDict, \
    stringToValue

from collections import Counter
from numpy import array, ndarray, dot, set_printoptions
from pathlib import Path

set_printoptions(precision=15)


def getSettingLines(sttng=None, maxSettingLength=0):
    """ TODO: integrate this into getSettings """

    assert isinstance(sttng, (Keyword, Block)), f'Setting {sttng} not a class of Keyword or Block'
    assert isinstance(maxSettingLength, int)

    if isinstance(sttng, Keyword):
        spaces = max(len(sttng.key), maxSettingLength)
        return [f'{sttng.key:<{spaces}s} : {sttng}']

    elif isinstance(sttng, Block):
        return [f'%block {sttng.key}'] + sttng.getLines() + [f'%endblock {sttng.key}']

    else:
        raise TypeError(f'Setting {sttng} not a class of Keyword or Block')


def getSettings(*keys, settings=None, attr=None):
    assert all(isinstance(key, str) for key in keys)
    assert isinstance(settings, list)
    assert all(isinstance(s, Setting) for s in settings)

    if attr is not None:
        assert isinstance(attr, str)
        attr = attr.strip().lower()
        assert attr in ('value', 'unit', 'lines')

    keys = [key.strip().lower() for key in keys]

    values = ()

    for key in keys:
        for s in settings:
            if key == s.key:

                if attr is None:
                    values += (s,)

                elif attr == 'value':
                    values += (s.getValue(),)

                elif attr == 'unit':
                    values += (s.getUnit(),)

                elif attr == 'lines':
                    values += (s.getLines(),)

                else:
                    raise ValueError(f'{attr} attribute/method not known for Setting')

                break
        else:
            values += (None,)

    values = values[0] if len(values) == 1 else values

    return values


def checkForUnit(lines=None, unitLine=0):
    assert isinstance(lines, list)
    assert isinstance(unitLine, int)

    try:
        potentialUnitLine = lines[unitLine]
    except IndexError:
        return None

    comment = potentialUnitLine.find('!')

    if comment != -1:
        potentialUnitLine = potentialUnitLine[:comment].strip()

    parts = potentialUnitLine.split()

    if len(parts) != 1:
        return None

    unit = parts[0]

    return unit


class Setting:
    def __init__(self, key=None):
        assert isinstance(key, str), 'Key for setting should be a string'
        key = key.strip().lower()

        # See if we can find the key in cells, then params, if not then we don't know what it is.
        if key in cellKnown:
            self.file = 'cell'
        elif key in paramKnown:
            self.file = 'param'
        else:
            raise ValueError(f'{key} not a known setting')

        self.key = key

        self.priority = getFromDict(key=key, dct=settingPriorities, strict=False, default=None)

        self.value = None
        self.unit = None

    def __repr__(self):
        return self.key

    def getValue(self):
        return self.value

    def getUnit(self):
        return self.unit


class Keyword(Setting):
    def __init__(self, key=None):
        super().__init__(key=key)


class BoolKeyword(Keyword):
    def __init__(self, key=None, value=None):
        super().__init__(key=key)

        assert value is True or value is False, f'Value of {value} not accepted for {self.key}, should be True or False'

        self.value = bool(value)

    def __str__(self):
        return str(self.value)


class StrKeyword(Keyword):
    def __init__(self, key=None, value=None):
        super().__init__(key=key)

        assert isinstance(value, str)

        value = value.strip().lower()

        assert value in settingValues.get(self.key, []), f'Value of {value} not accepted for {self.key}'

        self.value = getFromDict(key=value, dct=stringToNiceValue, strict=False, default=value)

    def __str__(self):
        return str(self.value)


class FloatKeyword(Keyword):
    def __init__(self, key=None, value=None, unit=None):
        super().__init__(key=key)

        assert isinstance(value, (int, float)), f'Value of {value} not accepted for {self.key}, should be an int or float'

        value = float(value)

        minimum = min(settingValues.get(self.key))
        maximum = max(settingValues.get(self.key))
        assertBetween(value, minimum=minimum, maximum=maximum, key=self.key)

        self.value = value

        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=settingUnits, strict=True)

        # self.format TODO: add a format variable

    def __str__(self):
        unit = '' if self.unit is None else self.unit
        return f'{self.value:<12.4f}  {unit}' if self.value >= 0.0001 else f'{self.value:<12.4E}  {unit}'


class IntKeyword(Keyword):
    def __init__(self, key=None, value=None, unit=None):
        super().__init__(key=key)

        assert isinstance(value, int), f'Value of {value} not accepted for {self.key}, should be an int'

        minimum = min(settingValues.get(self.key))
        maximum = max(settingValues.get(self.key))
        assertBetween(value, minimum=minimum, maximum=maximum, key=self.key)

        self.value = value

        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=settingUnits, strict=True)

        # self.format TODO: add a format variable

    def __str__(self):
        unit = '' if self.unit is None else self.unit
        return f'{self.value:<3d}  {unit}'


class VectorFloatKeyword(Keyword):
    def __init__(self, key=None, value=None, unit=None):
        super().__init__(key=key)

        try:
            value = array(value, dtype=float)
        except ValueError:
            raise ValueError(f'Value of {value} not accepted for {self.key}, should be a float array')

        minimum = min(settingValues.get(self.key))
        maximum = max(settingValues.get(self.key))
        assertBetween(*value, minimum=minimum, maximum=maximum, key=self.key)

        self.value = value

        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=settingUnits, strict=True)

        # self.format TODO: add a format variable

    def __str__(self):
        unit = '' if self.unit is None else self.unit
        return '  '.join('{:>15.12f}' for _ in range(len(self.value))).format(*self.value) + f'  {unit}'


class VectorIntKeyword(Keyword):
    def __init__(self, key=None, value=None, unit=None):
        super().__init__(key=key)

        try:
            value = array(value, dtype=int)
        except ValueError:
            raise ValueError(f'Value of {value} not accepted for {self.key}, should be an int array')

        minimum = min(settingValues.get(self.key))
        maximum = max(settingValues.get(self.key))
        assertBetween(*value, minimum=minimum, maximum=maximum, key=self.key)

        self.value = value

        self.unit = unit if unit is None else getUnit(key=key, unit=unit, unitTypes=settingUnits, strict=True)

        # self.format TODO: add a format variable

    def __str__(self):
        unit = '' if self.unit is None else self.unit
        return '  '.join('{:>3d}' for _ in range(len(self.value))).format(*self.value) + f'  {unit}'


class Block(Setting):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key)

        self.value = []

        self.lines = lines

        if lines is not None:
            assert isinstance(lines, list), 'Lines for block should be a list'
            assert all(isinstance(line, str) for line in lines), 'Each line for the block should be a string'

            lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('!')]

            self.lines = []

            for line in lines:
                # Check for comment.
                comment = line.find('!')

                # Remove it if need be.
                if comment != -1:
                    line = line[:comment].strip()

                self.lines.append(line)

    def __str__(self):
        return '; '.join(self.lines)

    def getLines(self):
        return self.lines


class ElementFloatBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        self.unit = 'RadSecTesla'

        if self.lines:
            linesToRead = self.lines

            # Check for unit line
            potentialUnit = checkForUnit(lines=self.lines, unitLine=0)
            potentialUnit = potentialUnit if potentialUnit is None else getUnit(key=key, unit=potentialUnit,
                                                                                unitTypes=settingUnits, strict=True)

            if potentialUnit is not None:
                self.unit = potentialUnit
                linesToRead = linesToRead[1:]

            for line in linesToRead:
                parts = line.split()

                assert len(parts) > 0, f'Error in {key} on line {line}'

                element = parts[0].strip().lower()

                assert element in elements, f'Element {element} not known'

                element = element[0].upper() + element[1:].lower()

                try:
                    value = float(parts[1])
                except ValueError:
                    raise ValueError(f'Error in {key} on line {line}')

                self.value.append((element, value))

    def __str__(self):
        return '; '.join(self.getLines())

    def getLines(self):
        unitPart = [self.unit] if self.unit is not None else []
        return unitPart + [f'{element:<3s}  {value:>15.12f}' for element, value in self.value]


class ElementThreeVectorFloatBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        self.unit = 'Ang' if self.key == 'positions_abs' else None  # TODO: add a default unit feature

        if self.lines:
            linesToRead = self.lines

            # Check for unit line
            potentialUnit = checkForUnit(lines=self.lines, unitLine=0)
            potentialUnit = potentialUnit if potentialUnit is None else getUnit(key=key, unit=potentialUnit,
                                                                                unitTypes=settingUnits, strict=True)

            if potentialUnit is not None:
                self.unit = potentialUnit
                linesToRead = linesToRead[1:]

            for line in linesToRead:
                parts = line.split()

                assert len(parts) > 0, f'Error in {key} on line {line}'

                element = parts[0].strip().lower()

                assert element in elements, f'Element {element} not known'

                element = element[0].upper() + element[1:].lower()

                try:
                    value = array(parts[1:], dtype=float)
                except ValueError:
                    raise ValueError(f'Error in {key} on line {line}')

                assert value.shape == (3,), f'Shape error in {key} on line {line}'

                self.value.append((element, value))

    def __str__(self):
        return '; '.join(self.getLines())

    def getLines(self):
        unitPart = [self.unit] if self.unit is not None else []
        return unitPart + [f'{element:<3s}  ' + '   '.join('{:>15.12f}' for _ in range(len(vector))).format(*vector) for (element, vector) in self.value]

    def findName(self):
        if not self.value:
            return None

        return ''.join([f'{element}{"" if num == 1 else num}' for element, num in Counter(list(zip(*self.value))[0]).items()])

    def rotate(self, rotationMatrix=None):
        assert isinstance(rotationMatrix, ndarray)
        assert rotationMatrix.shape == (3, 3)

        self.value = [(element, dot(rotationMatrix, vector)) for element, vector in self.value]

    # TODO: consider fractional coordinates
    '''
    def translate(self, translationVector=None, fromUnit='ang'):
        assert isinstance(translationVector, ndarray)
        assert translationVector.shape == (3, )

        assert isinstance(fromUnit, str)

        fromUnit = fromUnit.strip().lower()

        assert fromUnit in getAllowedUnits(unitType='length', strict=True)

        toUnit = self.unit if self.unit is not None else 'ang'  # Default in castep is ang

        # TODO: consider this unit conversion
        translationVector = unitConvert(fromUnit=fromUnit, toUnit=toUnit)

        self.value = {element: vector + translationVector for element, vector in self.value.items()}
    '''


class ThreeVectorFloatBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        self.unit = 'Ang' if self.key == 'lattice_cart' else 'Tesla' if self.key == 'external_bfield' else None  # TODO: add a default unit feature

        if self.lines:
            linesToRead = self.lines

            # Check for unit line
            potentialUnit = checkForUnit(lines=self.lines, unitLine=0)
            potentialUnit = potentialUnit if potentialUnit is None else getUnit(key=key, unit=potentialUnit,
                                                                                unitTypes=settingUnits, strict=True)

            if potentialUnit is not None:
                self.unit = potentialUnit
                linesToRead = linesToRead[1:]

            for line in linesToRead:
                try:
                    value = array(line.split(), dtype=float)
                except ValueError:
                    raise ValueError(f'Error in {key} on line {line}')

                assert value.shape == (3,), f'Shape error in {key} on line {line}'

                self.value.append(value)

    def __str__(self):
        return '; '.join(self.getLines())

    def getLines(self):
        unitPart = [self.unit] if self.unit is not None else []
        return unitPart + ['  ' + '   '.join('{:>15.12f}' for _ in range(len(vector))).format(*vector) for vector in self.value]

    def rotate(self, rotationMatrix=None):
        assert isinstance(rotationMatrix, ndarray)
        assert rotationMatrix.shape == (3, 3)

        self.value = [dot(rotationMatrix, vector) for vector in self.value]


class ThreeVectorFloatWeightedBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        for line in self.lines:
            try:
                value = array(line.split(), dtype=float)
            except ValueError:
                raise ValueError(f'Error in {key} on line {line}')

            assert value.shape == (4,), f'Shape error in {key} on line {line}'

            self.value.append(value)

    def __str__(self):
        return '; '.join(self.getLines())

    def getLines(self):
        return ['   '.join('{:>4.2f}' for _ in range(len(vector))).format(*vector) for vector in self.value]


class ThreeVectorIntBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        for line in self.lines:
            try:
                value = array(line.split(), dtype=int)
            except ValueError:
                raise ValueError(f'Error in {key} on line {line}')

            assert value.shape == (3,), f'Shape error in {key} on line {line}'

            self.value.append(value)

    def __str__(self):
        return '; '.join(self.getLines())

    def getLines(self):
        return ['  ' + '   '.join('{:>3d}' for _ in range(len(vector))).format(*vector) for vector in self.value]


class StrBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        self.value = self.lines


'''
class ElementStrBlock(Block):
    def __init__(self, key=None, lines=None):
        super().__init__(key=key, lines=lines)

        self.value = {}

        for line in self.lines:
            parts = line.split()

            assert len(parts) == 2, f'Error in {key} on line {line}'

            element, string = parts

            element = element.strip().lower()

            assert element in elements, f'Element {element} not known'

            element = element[0].upper() + element[1:].lower()

            self.value[element] = string

    def getLines(self):
        return [f'{element:<3s}  {string}' for element, string in self.value.items()]
'''

cellKnown = [
    # Lattice.
    'lattice_abc',
    'lattice_cart',

    # Positions.
    'positions_abs',
    'positions_frac',

    # Constraints.
    'cell_constraints',

    # Atomic data.
    'species_gamma',
    'species_pot',

    # Symmetry.
    'symmetry_ops',

    # Fields.
    'external_bfield',

    # Kpoints.
    'kpoint_list',
    'kpoints_list',
    'bs_kpoint_list',
    'bs_kpoints_list',
    'phonon_kpoint_list',
    'phonon_kpoints_list',
    'phonon_fine_kpoint_list',
    'optics_kpoint_list',
    'optics_kpoints_list',
    'magres_kpoint_list',
    'supercell_kpoint_list',
    'supercell_kpoints_list',
    'spectral_kpoint_list',
    'spectral_kpoints_list',

    # Keywords.
    'kpoint_mp_spacing',
    'kpoints_mp_spacing',
    'kpoint_mp_grid',
    'kpoints_mp_grid',
    'kpoint_mp_offset',
    'kpoints_mp_offset',
    'fix_all_cell',
    'fix_com',
    'symmetry_tol',
    'symmetry_generate'
]

cellPriorities = {
    # Lattice.
    'lattice_abc': 5.0,
    'lattice_cart': 10.0,

    # Positions.
    'positions_abs': 15.0,
    'positions_frac': 20.0,

    # Constraints.
    'cell_constraints': 25.0,

    # Atomic data.
    'species_gamma': 30.0,
    'species_pot': 35.0,

    # Symmetry.
    'symmetry_ops': 40.0,

    # Fields.
    'external_bfield': 45.0,

    # Kpoints.
    'kpoint_list': 50.0,
    'kpoints_list': 50.0,
    'bs_kpoint_list': 55.0,
    'bs_kpoints_list': 55.0,
    'phonon_kpoint_list': 60.0,
    'phonon_kpoints_list': 60.0,
    'phonon_fine_kpoint_list': 65.0,
    'optics_kpoint_list': 70.0,
    'optics_kpoints_list': 70.0,
    'magres_kpoint_list': 75.0,
    'supercell_kpoint_list': 80.0,
    'supercell_kpoints_list': 80.0,
    'spectral_kpoint_list': 85.0,
    'spectral_kpoints_list': 85.0,

    # Keywords.
    'kpoint_mp_spacing': 100.1,
    'kpoints_mp_spacing': 100.1,
    'kpoint_mp_grid': 100.2,
    'kpoints_mp_grid': 100.2,
    'kpoint_mp_offset': 100.3,
    'kpoints_mp_offset': 100.3,
    'fix_all_cell': 105.1,
    'fix_com': 105.2,
    'symmetry_tol': 110.1,
    'symmetry_generate': 110.2,
}

# cellDefaults = {}

cellTypes = {
    # Lattice.
    'lattice_abc': ThreeVectorFloatBlock,
    'lattice_cart': ThreeVectorFloatBlock,

    # Positions.
    'positions_abs': ElementThreeVectorFloatBlock,
    'positions_frac': ElementThreeVectorFloatBlock,

    # Constraints.
    'cell_constraints': ThreeVectorIntBlock,

    # Atomic data.
    'species_gamma': ElementFloatBlock,
    'species_pot': StrBlock,

    # Symmetry.
    'symmetry_ops': ThreeVectorFloatBlock,

    # Fields.
    'external_bfield': ThreeVectorFloatBlock,

    # Kpoints.
    'kpoint_list': ThreeVectorFloatWeightedBlock,
    'kpoints_list': ThreeVectorFloatWeightedBlock,
    'bs_kpoint_list': ThreeVectorFloatBlock,
    'bs_kpoints_list': ThreeVectorFloatBlock,
    'phonon_kpoint_list': ThreeVectorFloatBlock,
    'phonon_kpoints_list': ThreeVectorFloatBlock,
    'phonon_fine_kpoint_list': ThreeVectorFloatBlock,
    'optics_kpoint_list': ThreeVectorFloatWeightedBlock,
    'optics_kpoints_list': ThreeVectorFloatWeightedBlock,
    'magres_kpoint_list': ThreeVectorFloatWeightedBlock,
    'supercell_kpoint_list': ThreeVectorFloatWeightedBlock,
    'supercell_kpoints_list': ThreeVectorFloatWeightedBlock,
    'spectral_kpoint_list': ThreeVectorFloatWeightedBlock,
    'spectral_kpoints_list': ThreeVectorFloatWeightedBlock,

    # Keywords.
    'kpoint_mp_spacing': FloatKeyword,
    'kpoints_mp_spacing': FloatKeyword,
    'kpoint_mp_grid': VectorIntKeyword,
    'kpoints_mp_grid': VectorIntKeyword,
    'kpoint_mp_offset': VectorFloatKeyword,
    'kpoints_mp_offset': VectorFloatKeyword,
    'fix_all_cell': BoolKeyword,
    'fix_com': BoolKeyword,
    'symmetry_tol': FloatKeyword,
    'symmetry_generate': BoolKeyword
}

cellValues = {
    'kpoint_mp_spacing': [0.0, float('inf')],
    'kpoints_mp_spacing': [0.0, float('inf')],
    'kpoint_mp_grid': [0, float('inf')],
    'kpoints_mp_grid': [0, float('inf')],
    'kpoint_mp_offset': [-float('inf'), float('inf')],
    'kpoints_mp_offset': [-float('inf'), float('inf')],
    'symmetry_tol': [0.0, float('inf')]
}

cellUnits = {
    'lattice_abc': 'length',
    'lattice_cart': 'length',

    'positions_abs': 'length',
    'positions_frac': 'length',

    'species_gamma': 'gyromagnetic',

    'external_bfield': 'bfield',

    'kpoint_mp_spacing': 'inverselength',
    'kpoints_mp_spacing': 'inverselength',

    'symmetry_tol': 'length'
}

paramKnown = [  # task
    'task',
    'magres_task',
    'magres_method',
    'spectral_task',

    # general
    'xcfunctional',
    'opt_strategy',
    'cut_off_energy',
    'fix_occupancy',
    'basis_precision',
    'relativistic_treatment',

    # metals
    'smearing_width',
    'metals_method',
    'nextra_bands',

    # spin
    'spin',
    'spin_polarised',
    # 'spin_polarized',
    'spin_treatment',
    'spin_orbit_coupling',

    # bandstructure
    'bs_nbands',

    # phonons
    'phonon_method',
    'phonon_sum_rule',
    'phonon_fine_cutoff_method',

    # charge
    'charge',

    # calculate
    'calc_molecular_dipole',
    'popn_calculate',
    'calculate_raman',
    'calculate_densdiff',

    # write
    'write_cell_structure',
    'write_formatted_density',
    'popn_write',

    # units
    'dipole_unit',

    # miscellaneous.
    'max_scf_cycles',
    'num_dump_cycles',
    'elec_energy_tol',
    'bs_eigenvalue_tol',
    'elec_force_tol',
    'geom_force_tol',

    # extra
    'continuation',
    'reuse',
    'iprint',
    'opt_strategy_bias',
    'rand_seed',
    'comment',

    # blocks
    'devel_code'
]

paramPriorities = {  # task
    'task': 0.1,
    'magres_task': 0.2,
    'magres_method': 0.3,
    'spectral_task': 0.4,

    # general
    'xcfunctional': 1.1,
    'opt_strategy': 1.2,
    'cut_off_energy': 1.3,
    'fix_occupancy': 1.4,
    'basis_precision': 1.5,
    'relativistic_treatment': 1.6,

    # metals
    'smearing_width': 2.1,
    'metals_method': 2.2,
    'nextra_bands': 2.3,

    # spin
    'spin': 3.1,
    'spin_polarised': 3.2,
    # 'spin_polarized': 3.2,
    'spin_treatment': 3.3,
    'spin_orbit_coupling': 3.4,

    # bandstructure
    'bs_nbands': 4.1,

    # phonons
    'phonon_method': 5.1,
    'phonon_sum_rule': 5.2,
    'phonon_fine_cutoff_method': 5.3,

    # charge
    'charge': 6.1,

    # calculate
    'calc_molecular_dipole': 7.1,
    'popn_calculate': 7.2,
    'calculate_raman': 7.3,
    'calculate_densdiff': 7.4,

    # write
    'write_cell_structure': 8.1,
    'write_formatted_density': 8.2,
    'popn_write': 8.3,

    # units
    'dipole_unit': 9.1,

    # miscellaneous.
    'max_scf_cycles': 10.1,
    'num_dump_cycles': 10.2,
    'elec_energy_tol': 10.3,
    'bs_eigenvalue_tol': 10.4,
    'elec_force_tol': 10.5,
    'geom_force_tol': 10.6,

    # extra
    'continuation': 11.1,
    'reuse': 11.2,
    'iprint': 11.3,
    'opt_strategy_bias': 11.4,
    'rand_seed': 11.5,
    'comment': 11.6,

    # blocks
    'devel_code': 12.1
}

'''
paramDefaults = {
    # tasks
    'task': 'singlepoint',
    'magres_task': 'shielding',
    'magres_method': 'crystal',
    'spectral_task': 'bandstructure',

    # general
    'xcfunctional': 'lda',
    'opt_strategy': 'default',
    'cut_off_energy': 'set by basis_precision=fine',
    'fix_occupancy': 'false',
    'basis_precision': 'fine',
    'relativistic_treatment': 'koelling-harmon',

    # metals
    'smearing_width': '0.2 ev',
    'metals_method': 'dm',
    'nextra_bands': '0 if fix_occupancy else 4',

    # spin
    'spin': '0.0',
    'spin_polarised': 'true if spin > 0 else false',
    #'spin_polarized': 'true if spin > 0 else false',
    'spin_treatment': 'none',
    'spin_orbit_coupling': 'false',

    # bandstructure
    'bs_nbands': 'see castep --help bs_nbands',

    # phonons
    'phonon_method': 'set by phonon_fine_method',
    'phonon_sum_rule': 'false',
    'phonon_fine_cutoff_method': 'cumulant',

    # charge
    'charge': '0.0',

    # calculate
    'calc_molecular_dipole': 'false',
    'popn_calculate': 'true',
    'calculate_raman': 'false',
    'calculate_densdiff': 'false',

    # write
    'write_cell_structure': 'false',
    'write_formatted_density': 'false',
    'popn_write': 'enhanced',

    # units
    'dipole_unit': 'debye',

    # miscellaneous.
    'max_scf_cycles': '30',
    'num_dump_cycles': '0',
    'elec_energy_tol': '10^-5 eV for most tasks',
    'bs_eigenvalue_tol': '10^-6 eV/eig (10^-9 eV/eig if task=magres or phonon)',
    'elec_force_tol': 'set by elec_energy_tol',
    'geom_force_tol': '0.05 eV/Ang'

    # extra
    'continuation': 'null',
    'reuse': 'null',
    'iprint': '1',
    'opt_strategy_bias': 0,
    'rand_seed': 0,
    'comment': '(empty)'
}
'''

paramTypes = {
    # tasks
    'task': StrKeyword,
    'magres_task': StrKeyword,
    'magres_method': StrKeyword,
    'spectral_task': StrKeyword,

    # general
    'xcfunctional': StrKeyword,
    'opt_strategy': StrKeyword,
    'cut_off_energy': FloatKeyword,
    'fix_occupancy': BoolKeyword,
    'basis_precision': StrKeyword,
    'relativistic_treatment': StrKeyword,

    # metals
    'smearing_width': FloatKeyword,
    'metals_method': StrKeyword,
    'nextra_bands': IntKeyword,

    # spin
    'spin': FloatKeyword,
    'spin_polarised': BoolKeyword,
    # 'spin_polarized': BoolKeyword,
    'spin_treatment': StrKeyword,
    'spin_orbit_coupling': BoolKeyword,

    # bandstructure
    'bs_nbands': IntKeyword,

    # phonons
    'phonon_method': StrKeyword,
    'phonon_sum_rule': BoolKeyword,
    'phonon_fine_cutoff_method': StrKeyword,

    # charge
    'charge': FloatKeyword,

    # calculate
    'calc_molecular_dipole': BoolKeyword,
    'popn_calculate': BoolKeyword,
    'calculate_raman': BoolKeyword,
    'calculate_densdiff': BoolKeyword,

    # write
    'write_cell_structure': BoolKeyword,
    'write_formatted_density': BoolKeyword,
    'popn_write': BoolKeyword,

    # units
    'dipole_unit': StrKeyword,

    # miscellaneous.
    'max_scf_cycles': IntKeyword,
    'num_dump_cycles': IntKeyword,
    'elec_energy_tol': FloatKeyword,
    'bs_eigenvalue_tol': FloatKeyword,
    'elec_force_tol': FloatKeyword,
    'geom_force_tol': FloatKeyword,

    # extra
    'continuation': StrKeyword,
    'reuse': StrKeyword,
    'iprint': IntKeyword,
    'opt_strategy_bias': IntKeyword,
    'rand_seed': IntKeyword,
    'comment': StrKeyword,

    # blocks
    'devel_code': StrBlock
}

paramValues = {
    # tasks
    'task': ['singlepoint', 'bandstructure', 'geometryoptimisation', 'geometryoptimization', 'moleculardynamics', 'optics',
             'transitionstatesearch', 'phonon', 'efield', 'phonon+efield', 'thermodynamics', 'wannier', 'magres', 'elnes',
             'spectral', 'epcoupling', 'geneticalgor'],
    'magres_task': ['shielding', 'efg', 'nmr', 'gtensor', 'hyperfine', 'epr', 'jcoupling'],
    'magres_method': ['crystal', 'molecular', 'molecular3'],
    'spectral_task': ['bandstructure', 'dos', 'optics', 'coreloss', 'all'],

    # general
    'xcfunctional': ['lda', 'pw91', 'pbe', 'pbesol', 'rpbe', 'wc', 'blyp', 'lda-c', 'lda-x', 'zero', 'hf', 'pbe0', 'b3lyp',
                     'hse03', 'hse06', 'exx-x', 'hf-lda', 'exx', 'exx-lda', 'shf', 'sx', 'shf-lda', 'sx-lda', 'wda', 'sex',
                     'sex-lda', 'rscan'],
    'opt_strategy': ['default', 'speed', 'memory'],
    'cut_off_energy': [0.0, float('inf')],
    'basis_precision': ['null', 'coarse', 'medium', 'fine', 'precise', 'extreme'],
    'relativistic_treatment': ['koelling-harmon', 'schroedinger', 'zora', 'dirac'],

    # metals
    'smearing_width': [0.0, float('inf')],
    'metals_method': ['none', 'dm', 'edft'],
    'nextra_bands': [0.0, float('inf')],

    # spin
    'spin': [-float('inf'), float('inf')],
    'spin_treatment': ['none', 'scalar', 'vector'],

    # bandstructure
    'bs_nbands': [0, float('inf')],

    # phonons
    'phonon_method': ['dfpt', 'linearresponse', 'finitedisplacement'],
    'phonon_fine_cutoff_method': ['cumulant', 'spherical'],

    # charge
    'charge': [-float('inf'), float('inf')],

    # miscellaneous.
    'max_scf_cycles': [0, float('inf')],
    'num_dump_cycles': [0, float('inf')],
    'elec_energy_tol': [0.0, float('inf')],
    'bs_eigenvalue_tol': [0.0, float('inf')],
    'elec_force_tol': [0.0, float('inf')],
    'geom_force_tol': [0.0, float('inf')],

    # extra
    'iprint': [1, 2, 3],
    'opt_strategy_bias': [-3, -2, -1, 0, 1, 2, 3],
    'continuation': [Any(type_=str)],
    'reuse': [Any(type_=str)],
    'rand_seed': [-float('inf'), float('inf')],
}

paramUnits = {
    # general
    'cut_off_energy': 'energy',

    # metals
    'smearing_width': 'energy',

    # miscellaneous.
    'elec_energy_tol': 'energy',
    'bs_eigenvalue_tol': 'energy',
    'elec_force_tol': 'force',
    'geom_force_tol': 'force'
}

stringToNiceValue = {
    'lda': 'LDA',
    'pw91': 'PW91',
    'pbe': 'PBE',
    'pbesol': 'PBEsol',
    'rpbe': 'rPBE',
    'wc': 'WC',
    'blyp': 'BLYP',
    'lda-c': 'LDA-c',
    'lda-x': 'LDA-x',
    'zero': 'ZERO',
    'hf': 'HF',
    'pbe0': 'PBE0',
    'b3lyp': 'B3LYP',
    'hse03': 'HSE03',
    'hse06': 'HSE06',
    'exx-x': 'EXX-x',
    'hf-lda': 'HF-LDA',
    'exx': 'EXX',
    'exx-lda': 'EXX-LDA',
    'shf': 'SHF',
    'sx': 'SX',
    'shf-lda': 'SHF-LDA',
    'sx-lda': 'SX-LDA',
    'wda': 'WDA',
    'sex': 'SEX',
    'sex-lda': 'SEX-LDA',
    'rscan': 'rSCAN'
}

settingKnown = cellKnown + paramKnown
settingPriorities = cellPriorities | paramPriorities
settingTypes = cellTypes | paramTypes
settingValues = cellValues | paramValues
settingUnits = cellUnits | paramUnits

shortcutToCells = {'usp': StrBlock(key='species_pot', lines=[]),
                   'ncp': StrBlock(key='species_pot', lines=['NCP']),
                   'c19': StrBlock(key='species_pot', lines=['C19']),
                   'soc19': StrBlock(key='species_pot', lines=['SOC19']),

                   'h': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' BOHR',
                                                                          '  10.0   0.0   0.0',
                                                                          '   0.0  10.0   0.0',
                                                                          '   0.0   0.0  10.0']),

                         ElementThreeVectorFloatBlock(key='positions_abs', lines=['H   0.0  0.0  0.0']),

                         ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'hf': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                           '  10.0   0.0   0.0',
                                                                           '   0.0  10.0   0.0',
                                                                           '   0.0   0.0  10.0']),

                          # ElementThreeVectorFloatBlock(key='positions_frac',
                          #                             lines=['  H   0.1   0.1   0.099380480724825',
                          #                                    '  F   0.1   0.1   0.192319519275175']),

                          ElementThreeVectorFloatBlock(key='positions_abs',
                                                       lines=['  H   0.000000000000000   0.000000000000000   0.0000000000000000',
                                                              '  F   0.000000000000000   0.000000000000000   0.9293903855034999']),

                          ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'hcl': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           # ElementThreeVectorFloatBlock(key='positions_frac',
                           #                             lines=['  H    0.009999871806914   0.009999872045901   0.009226072370290',
                           #                                    '  Cl   0.010000128193086   0.010000127954099   0.138173927629710']),

                           ElementThreeVectorFloatBlock(key='positions_abs',
                                                        lines=['  H   0.000000000000000   0.000000000000000   0.0000000000000000',
                                                               '  Cl  0.000000000000000   0.000000000000000   1.2894785525992882']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'hclcrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                                   '5.01400000000000        0.00000000000000        0.00000000000000',
                                                                                   '0.00000000000000        4.38400000000000        0.00000000000000',
                                                                                   '0.00000000000000        0.00000000000000        4.60000000000000']),

                                  ElementThreeVectorFloatBlock(key='positions_frac',
                                                               lines=['H              0.500000000265469       0.452779682986140       0.004188482251491',
                                                                      'Cl             0.499999999734531       0.244220317013860       0.203811517748509']),

                                  VectorIntKeyword(key='kpoint_mp_grid', value=(2, 3, 3))],

                   'hbr': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  12.0   0.0   0.0',
                                                                            '   0.0  12.0   0.0',
                                                                            '   0.0   0.0  12.0']),

                           # ElementThreeVectorFloatBlock(key='positions_frac',
                           #                             lines=['  H    -0.000002946190640  -0.000003049675148   0.011117199951347',
                           #                                    '  Br    0.000002946190640   0.000003049675148   0.130282800048653']),

                           ElementThreeVectorFloatBlock(key='positions_abs',
                                                        lines=['  H   0.000000000000000   0.000000000000000   0.0000000000000000',
                                                               '  Br  0.000000000000000   0.000000000000000   1.4299872047889637']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hbrcrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                                '  5.7907   0.0   0.0',
                   #                                                                '   0.0  5.7907   0.0',
                   #                                                                '   0.0   0.0  5.7907']),

                   #               ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                            lines=['  H   0.081000000000000   0.121000000000000  -0.2020000000000000',
                   #                                                   '  Br  0.000000000000000   0.000000000000000   0.0000000000000000'])],

                   #               ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'hbrcrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                                   '  5.79070   0.00000   0.00000',
                                                                                   '  0.00000   5.79070   0.00000',
                                                                                   '  0.00000   0.00000   5.79070']),

                                  ElementThreeVectorFloatBlock(key='positions_frac',
                                                               lines=['  H   -0.006524933425476       0.026822316644399      -0.081086005113157',
                                                                      '  Br   0.106858226464315      -0.005926742706879       0.174857051791451']),

                                  VectorIntKeyword(key='kpoint_mp_grid', value=(2, 2, 2))],

                   'hi': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                           '  12.0   0.0   0.0',
                                                                           '   0.0  12.0   0.0',
                                                                           '   0.0   0.0  12.0']),

                          # ElementThreeVectorFloatBlock(key='positions_frac',
                          #                             lines=['  H   0.000000000013618   0.000000000163156  -0.000952894767401',
                          #                                    '  I  -0.000000000013618  -0.000000000163156   0.135036228100734']),

                          ElementThreeVectorFloatBlock(key='positions_abs',
                                                       lines=['  H   0.000000000000000   0.000000000000000   0.0000000000000000',
                                                              '  I   0.000000000000000   0.000000000000000   1.6318694744176200']),

                          ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hicrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                               '  3.48800   0.00000   0.00000',
                   #                                                               '  0.00000   3.48800   0.00000',
                   #                                                               '  0.00000   0.00000   2.82300']),

                   #              ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                           lines=['  H   0.500000	0.500000	0.500000',
                   #                                                  '  I   0.500000	0.000000	0.745000']),

                   #              ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'hicrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                                  '  3.48800   0.00000   0.00000',
                                                                                  '  0.00000   3.48800   0.00000',
                                                                                  '  0.00000   0.00000   2.82300']),

                                 ElementThreeVectorFloatBlock(key='positions_frac',
                                                              lines=['  H   0.143340111893670       0.296936395737313       0.105734023958144',
                                                                     '  I   0.143357135812752      -0.153587771884101       0.335286167327722']),

                                 VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 4))],

                   # 'hfrot': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                           '  10.0   0.0   0.0',
                   #                                                           '   0.0  10.0   0.0',
                   #                                                           '   0.0   0.0  10.0']),

                   #          ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                       # lines=['  H   0.12040092  0.12040092 -0.02972739',
                   #                                       #       '  F   0.16687044  0.16687044  0.03599044']),
                   #                                       lines=['H         0.120400920000000  0.120400920000000 -0.029727390000000',
                   #                                              'F         0.166870440000000  0.166870440000000  0.035990440000000']),

                   #          ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hclrot': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                            '  10.0   0.0   0.0',
                   #                                                            '   0.0  10.0   0.0',
                   #                                                            '   0.0   0.0  10.0']),

                   #           ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                        # lines=['  H    0.01168401  0.01168401 -0.00347605',
                   #                                        #       '  Cl   0.07615812  0.07615812  0.08770359']),
                   #                                        lines=['H         0.011684010000000  0.011684010000000 -0.003476050000000',
                   #                                               'Cl        0.076158120000000  0.076158120000000  0.087703590000000']),

                   #           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hbrrot': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                            '  12.0   0.0   0.0',
                   #                                                            '   0.0  12.0   0.0',
                   #                                                            '   0.0   0.0  12.0']),

                   #           ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                        # lines=['  H    0.00555653 0.00555643 0.00786405',
                   #                                        #       '  Br   0.06514347 0.06514357 0.09212085']),
                   #                                        lines=['H         0.005556530000000  0.005556430000000  0.007864050000000',
                   #                                               'Br        0.065143470000000  0.065143570000000  0.092120850000000']),

                   #           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hirot': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                           '  12.0   0.0   0.0',
                   #                                                           '   0.0  12.0   0.0',
                   #                                                           '   0.0   0.0  12.0']),

                   #          ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                       # lines=['  H   -0.00047645 -0.00047645 -0.0006738',
                   #                                       #       '  I    0.06751811  0.06751811  0.09548503']),
                   #                                       lines=['H        -0.000476450000000 -0.000476450000000 -0.000673800000000',
                   #                                              'I         0.067518110000000  0.067518110000000  0.095485030000000']),

                   #          ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hftrans': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                             '  10.0   0.0   0.0',
                   #                                                             '   0.0  10.0   0.0',
                   #                                                             '   0.0   0.0  10.0']),

                   #            ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                         lines=['  H   1.1   -1.1   2.099380480724825',
                   #                                                '  F   1.1   -1.1   2.192319519275175']),

                   #            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hcltrans': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                              '  10.0   0.0   0.0',
                   #                                                              '   0.0  10.0   0.0',
                   #                                                              '   0.0   0.0  10.0']),

                   #             ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                          lines=['  H    1.009999871806914  -1.009999872045901   2.009226072370290',
                   #                                                 '  Cl   1.010000128193086  -1.010000127954099   2.138173927629710']),

                   #             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hbrtrans': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                              '  12.0   0.0   0.0',
                   #                                                              '   0.0  12.0   0.0',
                   #                                                              '   0.0   0.0  12.0']),

                   #             ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                          lines=['  H     0.999997053809360  -1.000003049675148   2.011117199951347',
                   #                                                 '  Br    1.000002946190640  -0.999996950324852   2.130282800048653']),

                   #             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   # 'hitrans': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                   #                                                             '  12.0   0.0   0.0',
                   #                                                             '   0.0  12.0   0.0',
                   #                                                             '   0.0   0.0  12.0']),

                   #            ElementThreeVectorFloatBlock(key='positions_frac',
                   #                                         lines=['  H   1.000000000013618  -0.999999999836844   1.999047105232599',
                   #                                                '  I   0.999999999986382  -1.000000000163156   2.135036228100734']),

                   #            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'h2o': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac',
                                                        lines=['  H              0.000000138156747       0.077031227188196      -0.047227980384329',
                                                               '  H              0.000007512502009      -0.077030162679931      -0.047224848585106',
                                                               '  O             -0.000007650658757      -0.000001064508265       0.011999828969435']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'h2ocrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                                   '2.25969000000000       -3.91389788935532        0.00000000000000',
                                                                                   '2.25969000000000        3.91389788935532        0.00000000000000',
                                                                                   '0.00000000000000        0.00000000000000        7.35951000000000']),

                                  ElementThreeVectorFloatBlock(key='positions_frac',
                                                               lines=['H              0.449907681525901       0.899726237468610       0.021822099872174',
                                                                      'H              0.336743825296009       0.673582218996844       0.192851865258861',
                                                                      'O              0.330948493178090       0.661991543534546       0.061026034868965']),

                                  VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 2))],

                   'h2s': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac',
                                                        lines=['  H              0.000000013747163       0.097298365495616      -0.082532016386909',
                                                               '  H             -0.000000009675075      -0.097298367642218      -0.082532075331030',
                                                               '  S             -0.000000004072088       0.000000002146601       0.011690591717938']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'h2scrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                                   '4.93100000000000    0.00000000000000    0.00000000000000',
                                                                                   '0.00000000000000    4.93100000000000    0.00000000000000',
                                                                                   '0.00000000000000    0.00000000000000    4.93100000000000']),

                                  ElementThreeVectorFloatBlock(key='positions_frac',
                                                               lines=['H              0.435701473911940       0.248307316241313       0.054499064112790',
                                                                      'H              0.044298587979226       0.248307457102906       0.054498965660194',
                                                                      'S              0.239999938108834       0.239385226655781       0.247001970227016']),

                                  VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 3))],

                   'h2se': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  12.0   0.0   0.0',
                                                                             '   0.0  12.0   0.0',
                                                                             '   0.0   0.0  12.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.555659625038122       0.477529953917736       0.562528220437935',
                                                                'H              0.500417041851512       0.603533877552832       0.458200717174152',
                                                                'Se             0.465810294277033       0.487481759446099       0.479242275137913']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'h2te': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.578529313960992       0.498789506511651       0.484490269492563',
                                                                'H              0.657555205178195       0.602555755031231       0.629688329378706',
                                                                'Te             0.527359187444147       0.583072788040451       0.583288135962065']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'nh3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.000006407040808       0.100522912247874       0.000020324418027',
                                                                'H              0.087062109520791      -0.050268258621779       0.000012308306465',
                                                                'H             -0.087071182165915      -0.050270273463073       0.000010051596303',
                                                                'N              0.000002665604317       0.000005619836978      -0.000022684320795']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ph3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.000000515684409       0.118435336329655      -0.066195194593447',
                                                                'H              0.102565242149704      -0.059212051087251      -0.066200252966151',
                                                                'H             -0.102565293735021      -0.059213494258311      -0.066199366936981',
                                                                'P             -0.000000464099091       0.000000209015907       0.013714814496580']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ash3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.000001642150953       0.125269064249983      -0.081545515836112',
                                                                'H              0.108491839582588      -0.062642532763749      -0.081557394954852',
                                                                'H             -0.108489819744587      -0.062608509101231      -0.081576655533045',
                                                                'As            -0.000003661988954      -0.000008022385003       0.004849566324009']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'sbh3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.000011559425910       0.132302038520858      -0.088089576345866',
                                                                'H              0.122333592258257      -0.079347159955785      -0.098305809129754',
                                                                'H             -0.122339018428583      -0.079328164963500      -0.098325922028042',
                                                                'Sb            -0.000006133255584      -0.013616713601573       0.004891307503662']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch4': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac',
                                                        lines=['H              0.063267135480870       0.063267135449777       0.063267135843203',
                                                               'H             -0.063267510034405      -0.063267509752344       0.063270754345476',
                                                               'H             -0.063267509697432       0.063270755016364      -0.063267509771584',
                                                               'H              0.063270754570214      -0.063267509627021      -0.063267509798961',
                                                               'C             -0.000002870319246      -0.000002871086775      -0.000002870618134']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'sih4': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.085979145477420       0.085979169315231       0.085979135030576',
                                                                'H             -0.085979725956674      -0.085979758890426       0.085980334938600',
                                                                'H             -0.085979719475679       0.085980368204508      -0.085979732006461',
                                                                'H              0.085980311071081      -0.085979774172879      -0.085979732830018',
                                                                'Si            -0.000000011116149      -0.000000004456435      -0.000000005132697']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'geh4': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.087453716226487       0.087456771015751       0.087456958336816',
                                                                'H             -0.087460185505805      -0.087457368554614       0.087460865716999',
                                                                'H             -0.087460440119159       0.087460803553965      -0.087457285941680',
                                                                'H              0.087459270618156      -0.087459021213285      -0.087458960070307',
                                                                'Ge             0.000007638780321      -0.000001184801817      -0.000001578041828']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'snh4': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['H              0.098645132304870       0.098645162570146       0.098645145606710',
                                                                'H             -0.098645454893457      -0.098645424557504       0.098645694106483',
                                                                'H             -0.098645452909635       0.098645703608020      -0.098645437441890',
                                                                'H              0.098645681138657      -0.098645428349987      -0.098645444738852',
                                                                'Sn             0.000000094359565      -0.000000013270675       0.000000042467548']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'bh3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['H             -0.000000046956309       0.120023652918335       0.000000000176747',
                                                                                     'H              0.103945456385237      -0.060012168144273      -0.000000122419757',
                                                                                     'H             -0.103945442442255      -0.060012002581738       0.000000095853288',
                                                                                     'B              0.000000033013327       0.000000517807675       0.000000026389722']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'bf3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['B              0.000000002295232      -0.000001611645635       0.000000057383755',
                                                                                     'F              0.000000035661965       0.130356737684980       0.000000004782783',
                                                                                     'F              0.112883755529237      -0.065177563767529      -0.000000058091245',
                                                                                     'F             -0.112883793486434      -0.065177562271816      -0.000000004075293']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'bcl3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['B              0.000000045491317       0.000022203818438      -0.000000004253526',
                                                                                      'Cl             0.000000006942819       0.172691767811992       0.000000005145660',
                                                                                      'Cl             0.149569422621628      -0.086361994556501       0.000000002779216',
                                                                                      'Cl            -0.149569475055765      -0.086361977073928      -0.000000003671350']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'bbr3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['B             -0.000001893454796       0.000058991246653       0.000000639646940',
                                                                                      'Br             0.000003543727073       0.188753624312720       0.000002196652407',
                                                                                      'Br             0.163685986093486      -0.094406701001301      -0.000002630694046',
                                                                                      'Br            -0.163687636365763      -0.094405914558073      -0.000000205605300']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'bi3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['B              0.000001069361425       0.000074333468837       0.000000013224615',
                                                                                     'I             -0.000000036155453       0.210620209421039      -0.000000007155181',
                                                                                     'I              0.182447171614844      -0.105347380392697       0.000000014252738',
                                                                                     'I             -0.182448204820816      -0.105347162497179      -0.000000020322173']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3': [ThreeVectorFloatBlock(key='lattice_cart', lines=['BOHR',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_abs', lines=['ANG',
                                                                                    'C   0.000000000  0.000000000  0.000000000',
                                                                                    'H   1.079000000  0.000000000  0.000000000',
                                                                                    'H  -0.539500000  0.934441411  0.000000000',
                                                                                    'H  -0.539500000 -0.934441411  0.000000000']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch4distorted': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' Bohr',
                                                                                     '  10.0   0.0   0.0',
                                                                                     '   0.0  10.0   0.0',
                                                                                     '   0.0   0.0  10.0']),

                                    ElementThreeVectorFloatBlock(key='positions_abs', lines=['Bohr',
                                                                                             'C    0.10000  -0.20000  -0.10000',
                                                                                             'H    1.18913   1.18913   1.18913',
                                                                                             'H   -1.18913  -1.18913   1.18913',
                                                                                             'H   -1.18913   1.48913  -1.18913',
                                                                                             'H    1.28913  -1.18913  -1.18913']),

                                    ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'chf3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['H             -0.000000232023573       0.000002428372652       0.143856210456453',
                                                                                      'C              0.000000154403438      -0.000005020318294       0.033341052499049',
                                                                                      'F              0.000000157190429       0.124392677646440      -0.013106170119939',
                                                                                      'F              0.107730446528111      -0.062200107788081      -0.013105424288682',
                                                                                      'F             -0.107730526098405      -0.062199977912717      -0.013105668546881']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'chcl3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                              '  10.0   0.0   0.0',
                                                                              '   0.0  10.0   0.0',
                                                                              '   0.0   0.0  10.0']),

                             ElementThreeVectorFloatBlock(key='positions_frac', lines=['H             -0.000000324390107      -0.000003619033954       0.156640427146227',
                                                                                       'C              0.000000173232040       0.000014695836309       0.047115400621936',
                                                                                       'Cl             0.000000044324295       0.166583450903502      -0.006557901025921',
                                                                                       'Cl             0.144268136957555      -0.083297353017526      -0.006558902397767',
                                                                                       'Cl            -0.144268030123783      -0.083297174688331      -0.006559024344474']),

                             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'chbr3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                              '  10.0   0.0   0.0',
                                                                              '   0.0  10.0   0.0',
                                                                              '   0.0   0.0  10.0']),

                             ElementThreeVectorFloatBlock(key='positions_frac', lines=['H             -0.000000269274027      -0.000112145464671       0.162059506909919',
                                                                                       'C             -0.000002414947661      -0.000017154203052       0.052916412887490',
                                                                                       'Br             0.000006870657442       0.183006821652809      -0.004283578666009',
                                                                                       'Br             0.158370573268763      -0.091440452755585      -0.004322117317959',
                                                                                       'Br            -0.158374759704517      -0.091437069229501      -0.004320223813441']),

                             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'chi3': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['H             -0.000000321813961      -0.000185455342179       0.166129473792754',
                                                                                      'C              0.000001838275508       0.000086563772024       0.057025329128152',
                                                                                      'I              0.000002141639804       0.204708217627065      -0.002347842011162',
                                                                                      'I              0.177280712517976      -0.102308349292627      -0.002226749974936',
                                                                                      'I             -0.177284370619327      -0.102300976764284      -0.002230210934808']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3f': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.000000375922766       0.104092705133823      -0.101339471583022',
                                                                                      'H              0.090143571233639      -0.052046473539305      -0.101339289601869',
                                                                                      'H             -0.090143712256630      -0.052046790759686      -0.101339666576273',
                                                                                      'C             -0.000000155233994       0.000001159670187      -0.065095124522013',
                                                                                      'F             -0.000000079665780      -0.000000600505019       0.072617552283177']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3cl': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                              '  10.0   0.0   0.0',
                                                                              '   0.0  10.0   0.0',
                                                                              '   0.0   0.0  10.0']),

                             ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.000000154632103       0.103709699418708      -0.149914066242045',
                                                                                       'H              0.089811706282983      -0.051854852605322      -0.149914469407108',
                                                                                       'H             -0.089811718491282      -0.051855174672216      -0.149914677232760',
                                                                                       'C             -0.000000105759076       0.000001164964018      -0.114233805957249',
                                                                                       'Cl            -0.000000036664728      -0.000000837105188       0.062291418839162']),

                             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3br': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                              '  10.0   0.0   0.0',
                                                                              '   0.0  10.0   0.0',
                                                                              '   0.0   0.0  10.0']),

                             ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.000000145742961       0.103875853239954      -0.187525235990980',
                                                                                       'H              0.089956070227317      -0.051938191464794      -0.187525521894037',
                                                                                       'H             -0.089956092674304      -0.051938507571259      -0.187525738425637',
                                                                                       'C             -0.000000106026190       0.000001310242120      -0.153187388844230',
                                                                                       'Br            -0.000000017269784      -0.000000564446021       0.039329085154883']),

                             ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3i': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.000000197591365       0.104331050520609      -0.220304058210652',
                                                                                      'H              0.090347433142433      -0.052164658803372      -0.220304337450018',
                                                                                      'H             -0.090347460014346      -0.052165199678502      -0.220304752938509',
                                                                                      'C             -0.000000151250956      -0.000000098384899      -0.187299032588606',
                                                                                      'I             -0.000000019468496      -0.000001093653835       0.025693981187785']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'ch3icrystal': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                                    '  4.26760  0.00000  0.00000',
                                                                                    '   0.0000  6.57200  0.00000',
                                                                                    '   0.0000  0.00000  9.61100']),

                                   ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.307147473263237       0.400251941583500      -0.147760905664088',
                                                                                             'H              0.240891277785415       0.129003010792794      -0.164467231374899',
                                                                                             'H              0.592246516634888       0.222839114656347      -0.078144673478807',
                                                                                             'C              0.343060831396578       0.250222089069840      -0.100880441420287',
                                                                                             'I              0.109453900919883       0.247783843897520       0.094823251938080']),

                                   VectorIntKeyword(key='kpoint_mp_grid', value=(3, 2, 2))],

                   'co2': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['C             -0.000000002943713       0.000000000853473      -0.000000002809745',
                                                                                     'O              0.000000023434435       0.000000024116648       0.116221598922081',
                                                                                     'O             -0.000000020490722      -0.000000024970121      -0.116221596112336']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'cs2': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '  10.0   0.0   0.0',
                                                                            '   0.0  10.0   0.0',
                                                                            '   0.0   0.0  10.0']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['C              0.000000000877350       0.000000000532145      -0.000000037396101',
                                                                                     'S             -0.000000006711663       0.000000003144849       0.154948721513265',
                                                                                     'S              0.000000005834313      -0.000000003676994      -0.154948684117163']),

                           ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'cse2': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['C              0.000000242209340      -0.000000012445800       0.000000305194672',
                                                                                      'Se            -0.000000507102553       0.000000098891417       0.168647224010390',
                                                                                      'Se             0.000000264893214      -0.000000086445617      -0.168647529205062']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'cte2': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                             '  10.0   0.0   0.0',
                                                                             '   0.0  10.0   0.0',
                                                                             '   0.0   0.0  10.0']),

                            ElementThreeVectorFloatBlock(key='positions_frac', lines=['C              0.000000000000000       0.000000000000000       0.000000000000000',
                                                                                      'Te             0.000000000000000       0.000000000000000       0.191020000000000',
                                                                                      'Te             0.000000000000000       0.000000000000000      -0.191020000000000']),

                            ThreeVectorFloatWeightedBlock(key='kpoints_list', lines=['0.25 0.25 0.25 1.0'])],

                   'lih': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '3.99800000000000        0.00000000000000        0.00000000000000',
                                                                            '0.00000000000000        3.99800000000000        0.00000000000000',
                                                                            '0.00000000000000        0.00000000000000        3.99800000000000']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.500000000000000       0.500000000000000       0.500000000000000',
                                                                                     'Li             0.000000000000000       0.000000000000000       0.000000000000000']),

                           VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 3))],

                   'nah': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '4.78700000000000        0.00000000000000        0.00000000000000',
                                                                            '0.00000000000000        4.78700000000000        0.00000000000000',
                                                                            '0.00000000000000        0.00000000000000        4.78700000000000']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.500000000000000       0.500000000000000       0.500000000000000',
                                                                                     'Na             0.000000000000000       0.000000000000000       0.000000000000000']),

                           VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 3))],

                   'kh': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                           '5.70100000000000        0.00000000000000        0.00000000000000',
                                                                           '0.00000000000000        5.70100000000000        0.00000000000000',
                                                                           '0.00000000000000        0.00000000000000        5.70100000000000']),

                          ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.500000000000000       0.500000000000000       0.500000000000000',
                                                                                    'K              0.000000000000000       0.000000000000000       0.000000000000000']),

                          VectorIntKeyword(key='kpoint_mp_grid', value=(2, 2, 2))],

                   'rbh': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '6.07500000000000        0.00000000000000        0.00000000000000',
                                                                            '0.00000000000000        6.07500000000000        0.00000000000000',
                                                                            '0.00000000000000        0.00000000000000        6.07500000000000']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.500000000000000       0.500000000000000       0.500000000000000',
                                                                                     'Rb             0.000000000000000       0.000000000000000       0.000000000000000']),

                           VectorIntKeyword(key='kpoint_mp_grid', value=(2, 2, 2))],

                   'csh': [ThreeVectorFloatBlock(key='lattice_cart', lines=[' ANG',
                                                                            '6.43900000000000        0.00000000000000        0.00000000000000',
                                                                            '0.00000000000000        6.43900000000000        0.00000000000000',
                                                                            '0.00000000000000        0.00000000000000        6.43900000000000']),

                           ElementThreeVectorFloatBlock(key='positions_frac', lines=['H              0.500000000000000       0.500000000000000       0.500000000000000',
                                                                                     'Cs             0.000000000000000       0.000000000000000       0.000000000000000']),

                           VectorIntKeyword(key='kpoint_mp_grid', value=(2, 2, 2))],

                   'cs2so4': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                               '8.21800000000000        0.00000000000000        0.00000000000000',
                                                                               '0.00000000000000        10.9160000000000        0.00000000000000',
                                                                               '0.00000000000000        0.00000000000000        6.24400000000000']),

                              ElementThreeVectorFloatBlock(key='positions_frac',
                                                           lines=['O                0.058958294239792       0.412296604835396       0.250000000000000',
                                                                  'O                0.941041705760209       0.587703395164604       0.750000000000000',
                                                                  'O                0.441041705760208       0.912296604835396       0.750000000000000',
                                                                  'O                0.558958294239791       0.087703395164604       0.250000000000000',
                                                                  'O                0.296396719119591       0.546940770721560       0.250000000000000',
                                                                  'O                0.703603280880409       0.453059229278440       0.750000000000000',
                                                                  'O                0.203603280880409       0.046940770721560       0.750000000000000',
                                                                  'O                0.796396719119591       0.953059229278440       0.250000000000000',
                                                                  'O                0.303460811266330       0.354388483777610       0.055105053463658',
                                                                  'O                0.696539188733670       0.645611516222390       0.555105053463658',
                                                                  'O                0.196539188733670       0.854388483777610       0.555105053463658',
                                                                  'O                0.696539188733670       0.645611516222390       0.944894946536342',
                                                                  'O                0.196539188733670       0.854388483777610       0.944894946536342',
                                                                  'O                0.303460811266330       0.354388483777610       0.444894946536342',
                                                                  'O                0.803460811266330       0.145611516222390       0.444894946536342',
                                                                  'O                0.803460811266330       0.145611516222390       0.055105053463658',
                                                                  'S                0.239407001154618       0.417080591657507       0.250000000000000',
                                                                  'S                0.760592998845382       0.582919408342493       0.750000000000000',
                                                                  'S                0.260592998845382       0.917080591657507       0.750000000000000',
                                                                  'S                0.739407001154618       0.082919408342493       0.250000000000000',
                                                                  'Cs               0.677062148835080       0.409541881327826       0.250000000000000',
                                                                  'Cs               0.322937851164920       0.590458118672175       0.750000000000000',
                                                                  'Cs               0.822937851164920       0.909541881327825       0.750000000000000',
                                                                  'Cs               0.177062148835080       0.090458118672174       0.250000000000000',
                                                                  'Cs               0.989070462240866       0.701415486622290       0.250000000000000',
                                                                  'Cs               0.010929537759134       0.298584513377710       0.750000000000000',
                                                                  'Cs               0.510929537759134       0.201415486622290       0.750000000000000',
                                                                  'Cs               0.489070462240866       0.798584513377710       0.250000000000000']),

                              VectorIntKeyword(key='kpoint_mp_grid', value=(2, 1, 2))],

                   'csclo4': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                               '9.82300000000000        0.00000000000000        0.00000000000000',
                                                                               '0.00000000000000        6.00900000000000        0.00000000000000',
                                                                               '0.00000000000000        0.00000000000000        7.76400000000000']),

                              ElementThreeVectorFloatBlock(key='positions_frac',
                                                           lines=['O                0.920815776598092       0.250000000000000       0.623924739664073',
                                                                  'O                0.579184223401908       0.750000000000000       0.123924739664073',
                                                                  'O                0.079184223401908       0.750000000000000       0.376075260335927',
                                                                  'O                0.420815776598092       0.250000000000000       0.876075260335927',
                                                                  'O                0.158426256969978       0.250000000000000       0.561596380578775',
                                                                  'O                0.341573743030022       0.750000000000000       0.061596380578775',
                                                                  'O                0.841573743030022       0.750000000000000       0.438403619421225',
                                                                  'O                0.658426256969978       0.250000000000000       0.938403619421225',
                                                                  'O                0.074091374986122       0.052485874217298       0.803574686693282',
                                                                  'O                0.425908625013878       0.552485874217298       0.303574686693282',
                                                                  'O                0.425908625013878       0.947514125782702       0.303574686693282',
                                                                  'O                0.925908625013878       0.552485874217298       0.196425313306718',
                                                                  'O                0.925908625013878       0.947514125782702       0.196425313306718',
                                                                  'O                0.574091374986122       0.447514125782702       0.696425313306718',
                                                                  'O                0.574091374986122       0.052485874217298       0.696425313306718',
                                                                  'O                0.074091374986122       0.447514125782702       0.803574686693282',
                                                                  'Cl               0.056441686025486       0.250000000000000       0.696700536608201',
                                                                  'Cl               0.443558313974514       0.750000000000000       0.196700536608202',
                                                                  'Cl               0.943558313974514       0.750000000000000       0.303299463391799',
                                                                  'Cl               0.556441686025486       0.250000000000000       0.803299463391799',
                                                                  'Cs               0.188917879036478       0.250000000000000       0.162638037839053',
                                                                  'Cs               0.311082120963522       0.750000000000000       0.662638037839053',
                                                                  'Cs               0.811082120963522       0.750000000000000       0.837361962160947',
                                                                  'Cs               0.688917879036478       0.250000000000000       0.337361962160947']),

                              VectorIntKeyword(key='kpoint_mp_grid', value=(2, 2, 2))],

                   'biocl': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                              '3.89200000000000        0.00000000000000        0.00000000000000',
                                                                              '0.00000000000000        3.89200000000000        0.00000000000000',
                                                                              '0.00000000000000        0.00000000000000        7.37100000000000']),

                                ElementThreeVectorFloatBlock(key='positions_frac',
                                                             lines=['O                0.250000000000000       0.750000000000000      -0.000000000000000',
                                                                    'O                0.750000000000000       0.250000000000000       0.000000000000000',
                                                                    'Cl               0.250000000000000       0.250000000000000       0.645765135720724',
                                                                    'Cl               0.750000000000000       0.750000000000000       0.354234864279276',
                                                                    'Bi               0.250000000000000       0.250000000000000       0.176740075568957',
                                                                    'Bi               0.750000000000000       0.750000000000000       0.823259924431043']),

                                VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 2))],

                   'biobr': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                              '3.92330000000000        0.00000000000000        0.00000000000000',
                                                                              '0.00000000000000        3.92330000000000        0.00000000000000',
                                                                              '0.00000000000000        0.00000000000000        8.10500000000000']),

                             ElementThreeVectorFloatBlock(key='positions_frac',
                                                          lines=['O                0.250000000000000       0.750000000000000      -0.000000000000000',
                                                                 'O                0.750000000000000       0.250000000000000       0.000000000000000',
                                                                 'Br               0.250000000000000       0.250000000000000       0.657143576885767',
                                                                 'Br               0.750000000000000       0.750000000000000       0.342856423114233',
                                                                 'Bi               0.250000000000000       0.250000000000000       0.158960698224365',
                                                                 'Bi               0.750000000000000       0.750000000000000       0.841039301775635']),

                             VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 2))],

                   'bioi': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                             '3.99150000000000        0.00000000000000        0.00000000000000',
                                                                             '0.00000000000000        3.99150000000000        0.00000000000000',
                                                                             '0.00000000000000        0.00000000000000        9.15010000000000']),

                            ElementThreeVectorFloatBlock(key='positions_frac',
                                                         lines=['O                0.000000000000000       0.000000000000000      -0.000000000000000',
                                                                'O                0.500000000000000       0.500000000000000       0.000000000000000',
                                                                'I                0.000000000000000       0.500000000000000       0.667763179407819',
                                                                'I                0.500000000000000       0.000000000000000       0.332236820592181',
                                                                'Bi               0.000000000000000       0.500000000000000       0.138099436556996',
                                                                'Bi               0.500000000000000       0.000000000000000       0.861900563443004']),

                            VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 2))],

                   'bialteo6': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                                 '4.38789091335462       -2.53335000000000        0.00000000000000',
                                                                                 '0.00000000000000        5.06670000000000        0.00000000000000',
                                                                                 '0.00000000000000        0.00000000000000        4.99200000000000']),

                                ElementThreeVectorFloatBlock(key='positions_frac',
                                                             lines=['O                0.630860635049577       0.618919538549504       0.215786701751868',
                                                                    'O                0.381080461450496       0.369139364950422       0.784213298248132',
                                                                    'O                0.988058903499926       0.618919538549504       0.784213298248132',
                                                                    'O                0.381080461450496       0.011941096500074       0.215786701751868',
                                                                    'O                0.988058903499926       0.369139364950422       0.215786701751868',
                                                                    'O                0.630860635049577       0.011941096500074       0.784213298248132',
                                                                    'Al               0.666666666666667       0.333333333333333       0.000000000000000',
                                                                    'Te               0.333333333333333       0.666666666666667       0.000000000000000',
                                                                    'Bi               0.000000000000000      -0.000000000000000       0.500000000000000']),

                                VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 3))],

                   'bigateo6': [ThreeVectorFloatBlock(key='lattice_cart', lines=['ANG',
                                                                                 '4.42279173712713       -2.55350000000000        0.00000000000000',
                                                                                 '0.00000000000000        5.10700000000000        0.00000000000000',
                                                                                 '0.00000000000000        0.00000000000000        4.93200000000000']),

                                ElementThreeVectorFloatBlock(key='positions_frac',
                                                             lines=['O                0.372323605617923      -0.002636938728761       0.276942444273406',
                                                                    'O                1.002636938728761       0.627676394382077       0.723057555726594',
                                                                    'O                0.625039455653316      -0.002636938728761       0.723057555726594',
                                                                    'O                1.002636938728761       0.374960544346684       0.276942444273406',
                                                                    'O                0.625039455653316       0.627676394382077       0.276942444273406',
                                                                    'O                0.372323605617923       0.374960544346684       0.723057555726594',
                                                                    'Ga               0.333333333333333       0.666666666666667       0.500000000000000',
                                                                    'Te               0.666666666666667       0.333333333333333       0.500000000000000',
                                                                    'Bi               0.000000000000000      -0.000000000000000       0.000000000000000']),

                                VectorIntKeyword(key='kpoint_mp_grid', value=(3, 3, 3))]

                   }

shortcutToCellsAliases = {}

shortcutToParams = {'singlepoint': StrKeyword(key='task', value='singlepoint'),
                    'geometryoptimisation': StrKeyword(key='task', value='geometryoptimisation'),

                    'lda': StrKeyword(key='xcfunctional', value='lda'),
                    'pbe': StrKeyword(key='xcfunctional', value='pbe'),
                    'pw91': StrKeyword(key='xcfunctional', value='pw91'),
                    'b3lyp': StrKeyword(key='xcfunctional', value='b3lyp'),

                    'lowcutoff': FloatKeyword(key='cut_off_energy', value=300.0, unit='eV'),
                    'normalcutoff': FloatKeyword(key='cut_off_energy', value=500.0, unit='eV'),
                    'cutoff': FloatKeyword(key='cut_off_energy', value=700.0, unit='eV'),
                    'highcutoff': FloatKeyword(key='cut_off_energy', value=900.0, unit='eV'),

                    'schroedinger': StrKeyword(key='relativistic_treatment', value='schroedinger'),
                    'dirac': StrKeyword(key='relativistic_treatment', value='dirac'),

                    'spinpolarised': BoolKeyword(key='spin_polarised', value=True),

                    'efg': [StrKeyword(key='task', value='magres'),
                            StrKeyword(key='magres_task', value='efg')],

                    'shielding': [StrKeyword(key='task', value='magres'),
                                  StrKeyword(key='magres_task', value='shielding')],

                    'nmr': [StrKeyword(key='task', value='magres'),
                            StrKeyword(key='magres_task', value='nmr')],

                    'hyperfine': [StrKeyword(key='task', value='magres'),
                                  StrKeyword(key='magres_task', value='hyperfine')],

                    # 'jcoupling': (!) NotImplementedError,

                    'soc': [BoolKeyword(key='spin_polarised', value=True),
                            StrKeyword(key='spin_treatment', value='vector'),
                            BoolKeyword(key='spin_orbit_coupling', value=True),
                            StrBlock(key='species_pot', lines=['SOC19'])],

                    'writecell': BoolKeyword(key='write_cell_structure', value=True),

                    'iprint1': IntKeyword(key='iprint', value=1),
                    'iprint2': IntKeyword(key='iprint', value=2),
                    'iprint3': IntKeyword(key='iprint', value=3),
                    'iprint': IntKeyword(key='iprint', value=3),

                    'continuation': StrKeyword(key='continuation', value='default'),

                    'randseed': IntKeyword(key='rand_seed', value=1234567),

                    'xdensity': StrBlock('devel_code', lines=['density_in_x=true']),
                    'ydensity': StrBlock('devel_code', lines=['density_in_y=true']),
                    'zdensity': StrBlock('devel_code', lines=['density_in_z=true'])
                    }

shortcutToParamsAliases = {'geom': [shortcutToParams.get('geometryoptimisation'),
                                    shortcutToParams.get('writecell'),
                                    shortcutToParams.get('iprint1')],
                           'geometry': [shortcutToParams.get('geometryoptimisation'),
                                        shortcutToParams.get('writecell'),
                                        shortcutToParams.get('iprint1')],
                           'optimise': [shortcutToParams.get('geometryoptimisation'),
                                        shortcutToParams.get('writecell'),
                                        shortcutToParams.get('iprint1')],
                           'optimize': [shortcutToParams.get('geometryoptimisation'),
                                        shortcutToParams.get('writecell'),
                                        shortcutToParams.get('iprint1')],
                           'optimisation': [shortcutToParams.get('geometryoptimisation'),
                                            shortcutToParams.get('writecell'),
                                            shortcutToParams.get('iprint1')],
                           'optimization': [shortcutToParams.get('geometryoptimisation'),
                                            shortcutToParams.get('writecell'),
                                            shortcutToParams.get('iprint1')],
                           'geometryoptimization': [shortcutToParams.get('geometryoptimisation'),
                                                    shortcutToParams.get('writecell'),
                                                    shortcutToParams.get('iprint1')],

                           'averagecutoff': shortcutToParams.get('normalcutoff'),
                           'middlecutoff': shortcutToParams.get('normalcutoff'),
                           'mediumcutoff': shortcutToParams.get('normalcutoff'),

                           'schrod': shortcutToParams.get('schroedinger'),
                           'schrodinger': shortcutToParams.get('schroedinger'),
                           'schroed': shortcutToParams.get('schroedinger'),

                           'polarised': shortcutToParams.get('spinpolarised'),
                           'polarized': shortcutToParams.get('spinpolarised'),
                           'spinpolarized': shortcutToParams.get('spinpolarised'),
                           'spin_polarised': shortcutToParams.get('spinpolarised'),
                           'spin_polarized': shortcutToParams.get('spinpolarised'),

                           'writestructure': shortcutToParams.get('writecell')
                           }

stringToVariableSettings = {'soc': [(StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),
                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False)),
                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True))],

                            'density': [StrBlock(key='devel_code', lines=['density_in_x=true']),
                                        StrBlock(key='devel_code', lines=['density_in_y=true']),
                                        StrBlock(key='devel_code', lines=['density_in_z=true'])],

                            'bfielddensity': [
                                (StrBlock(key='devel_code', lines=['density_in_x=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '500.0 0.0 0.0'])),
                                (StrBlock(key='devel_code', lines=['density_in_y=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 500.0 0.0'])),
                                (StrBlock(key='devel_code', lines=['density_in_z=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 500.0']))],

                            'bfielddensityneg': [
                                (StrBlock(key='devel_code', lines=['density_in_x=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '-500.0 0.0 0.0'])),
                                (StrBlock(key='devel_code', lines=['density_in_y=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 -500.0 0.0'])),
                                (StrBlock(key='devel_code', lines=['density_in_z=true']), ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 -500.0']))],

                            'socdensity': [(StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                           (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                           (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                            StrBlock(key='devel_code', lines=['density_in_x=true'])),

                                           (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                            StrBlock(key='devel_code', lines=['density_in_y=true'])),

                                           (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                            StrBlock(key='devel_code', lines=['density_in_z=true']))],

                            'vectordensity': [(StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                              (StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                               StrBlock(key='devel_code', lines=['density_in_x=true'])),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                               StrBlock(key='devel_code', lines=['density_in_y=true'])),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                               StrBlock(key='devel_code', lines=['density_in_z=true'])),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                               StrBlock(key='devel_code', lines=['density_in_x=true'])),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                               StrBlock(key='devel_code', lines=['density_in_y=true'])),

                                              (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                               StrBlock(key='devel_code', lines=['density_in_z=true']))],

                            'vectordensitybfield': [(StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                                    (StrKeyword(key='spin_treatment', value='scalar'), BoolKeyword(key='spin_orbit_coupling', value=False)),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                                     StrBlock(key='devel_code', lines=['density_in_x=true'])),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                                     StrBlock(key='devel_code', lines=['density_in_y=true'])),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=False),
                                                     StrBlock(key='devel_code', lines=['density_in_z=true'])),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                                     StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '500.0 0.0 0.0'])),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                                     StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 500.0 0.0'])),

                                                    (StrKeyword(key='spin_treatment', value='vector'), BoolKeyword(key='spin_orbit_coupling', value=True),
                                                     StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 500.0']))],

                            'hyperfinebfield': [(StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 1.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 1.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '2.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 2.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 2.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '3.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 3.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 3.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '4.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 4.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 4.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '5.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 5.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 5.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '6.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 6.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 6.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '7.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 7.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 7.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '8.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 8.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 8.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '9.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 9.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 9.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 10.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 10.0']))
                                                ],

                            'hyperfinetensbfield': [(StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 10.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 10.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '20.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 20.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 20.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '30.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 30.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 30.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '40.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 40.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 40.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '50.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 50.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 50.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '60.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 60.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 60.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '70.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 70.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 70.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '80.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 80.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 80.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '90.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 90.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 90.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '100.0 0.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 100.0 0.0'])),

                                                    (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                     ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 100.0']))
                                                    ],

                            'hyperfinehundredsbfield': [(StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '100.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 100.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 100.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '200.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 200.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 200.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '300.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 300.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 300.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '400.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 400.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 400.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '500.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 500.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 500.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '600.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 600.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 600.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '700.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 700.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 700.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '800.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 800.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 800.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '900.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 900.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 900.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1000.0 0.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 1000.0 0.0'])),

                                                        (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                         ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 1000.0']))
                                                        ],

                            'hyperfinekilosbfield': [(StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 1000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 1000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '2000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 2000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 2000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '3000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 3000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 3000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '4000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 4000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 4000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '5000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 5000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 5000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '6000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 6000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 6000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '7000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 7000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 7000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '8000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 8000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 8000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '9000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 9000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 9000.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10000.0 0.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 10000.0 0.0'])),

                                                     (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                      ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 10000.0']))
                                                     ],

                            'bfieldlinearity': [(StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 1.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 1.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '2.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 2.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 2.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '3.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 3.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 3.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '4.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 4.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 4.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '5.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 5.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 5.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '6.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 6.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 6.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '7.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 7.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 7.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '8.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 8.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 8.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '9.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 9.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 9.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 10.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 10.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '20.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 20.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 20.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '30.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 30.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 30.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '40.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 40.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 40.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '50.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 50.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 50.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '60.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 60.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 60.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '70.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 70.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 70.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '80.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 80.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 80.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '90.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 90.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 90.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '100.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 100.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 100.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '200.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 200.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 200.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '300.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 300.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 300.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '400.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 400.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 400.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '500.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 500.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 500.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '600.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 600.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 600.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '700.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 700.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 700.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '800.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 800.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 800.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '900.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 900.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 900.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 1000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 1000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '2000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 2000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 2000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '3000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 3000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 3000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '4000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 4000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 4000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '5000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 5000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 5000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '6000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 6000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 6000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '7000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 7000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 7000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '8000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 8000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 8000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '9000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 9000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 9000.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_x=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10000.0 0.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_y=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 10000.0 0.0'])),

                                                (StrBlock(key='devel_code', lines=['density_in_z=true']),
                                                 ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0 0.0 10000.0']))
                                                ],

                            'xbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 0.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 1.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 2.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 3.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 4.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 5.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 6.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 7.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 8.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 9.0  0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10.0  0.0   0.0'])],

                            'ybfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   1.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   2.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   3.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   4.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   5.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   6.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   7.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   8.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   9.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0  10.0   0.0'])],

                            'zbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   0.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   1.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   2.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   3.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   4.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   5.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   6.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   7.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   8.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   9.0']),
                                        ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0  10.0'])],

                            'tensxbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 0.0   0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 10.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 20.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 30.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 40.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 50.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 60.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 70.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 80.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 90.0  0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '100.0  0.0   0.0'])],

                            'tensybfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0    0.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   10.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   20.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   30.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   40.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   50.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   60.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   70.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   80.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   90.0   0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0  100.0   0.0'])],

                            'tenszbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0    0.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   10.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   20.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   30.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   40.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   50.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   60.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   70.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   80.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   90.0']),
                                            ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0  100.0'])],

                            'hundredsxbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 0.0   0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 100.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 200.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 300.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 400.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 500.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 600.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 700.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 800.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 900.0  0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '1000.0  0.0   0.0'])],

                            'hundredsybfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0    0.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   100.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   200.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   300.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   400.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   500.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   600.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   700.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   800.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   900.0   0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0  1000.0   0.0'])],

                            'hundredszbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0    0.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   100.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   200.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   300.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   400.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   500.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   600.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   700.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   800.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   900.0']),
                                                ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0  1000.0'])],

                            'kilosxbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 0.0   0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 1000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 2000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 3000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 4000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 5000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 6000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 7000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 8000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', ' 9000.0  0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '10000.0  0.0   0.0'])],

                            'kilosybfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0    0.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   1000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   2000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   3000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   4000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   5000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   6000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   7000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   8000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   9000.0   0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0  10000.0   0.0'])],

                            'kiloszbfield': [ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0    0.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   1000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   2000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   3000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   4000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   5000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   6000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   7000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   8000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0   9000.0']),
                                             ThreeVectorFloatBlock(key='external_bfield', lines=['TESLA', '0.0   0.0  10000.0'])],

                            'halides': [shortcutToCells.get('hf'),
                                        shortcutToCells.get('hcl'),
                                        shortcutToCells.get('hbr'),
                                        shortcutToCells.get('hi')],

                            'halidecrystals': [shortcutToCells.get('hclcrystal'),
                                               shortcutToCells.get('hbrcrystal'),
                                               shortcutToCells.get('hicrystal')],

                            # 'halidesrot': [shortcutToCells.get('hfrot'),
                            #               shortcutToCells.get('hclrot'),
                            #               shortcutToCells.get('hbrrot'),
                            #               shortcutToCells.get('hirot')],

                            # 'halidestrans': [shortcutToCells.get('hftrans'),
                            #                 shortcutToCells.get('hcltrans'),
                            #                 shortcutToCells.get('hbrtrans'),
                            #                 shortcutToCells.get('hitrans')],

                            'hydrogenhalides': [shortcutToCells.get('hf'),
                                                shortcutToCells.get('hcl'),
                                                shortcutToCells.get('hbr'),
                                                shortcutToCells.get('hi')],

                            'hydrogenhalidecrystals': [shortcutToCells.get('hclcrystal'),
                                                       shortcutToCells.get('hbrcrystal'),
                                                       shortcutToCells.get('hicrystal')],

                            'chalcogenides': [shortcutToCells.get('h2o'),
                                              shortcutToCells.get('h2s'),
                                              shortcutToCells.get('h2se'),
                                              shortcutToCells.get('h2te')],

                            'carbonchalcogenides': [shortcutToCells.get('co2'),
                                                    shortcutToCells.get('cs2'),
                                                    shortcutToCells.get('cse2'),
                                                    shortcutToCells.get('cte2')],

                            'pnictides': [shortcutToCells.get('nh3'),
                                          shortcutToCells.get('ph3'),
                                          shortcutToCells.get('ash3'),
                                          shortcutToCells.get('sbh3')],

                            'carbongroup': [shortcutToCells.get('ch4'),
                                            shortcutToCells.get('sih4'),
                                            shortcutToCells.get('geh4'),
                                            shortcutToCells.get('snh4')],

                            'methylhalides': [shortcutToCells.get('ch3f'),
                                              shortcutToCells.get('ch3cl'),
                                              shortcutToCells.get('ch3br'),
                                              shortcutToCells.get('ch3i')],

                            'alkalihydrides': [shortcutToCells.get('lih'),
                                               shortcutToCells.get('nah'),
                                               shortcutToCells.get('kh'),
                                               shortcutToCells.get('rbh'),
                                               shortcutToCells.get('csh')],

                            'boronhalides': [shortcutToCells.get('bf3'),
                                             shortcutToCells.get('bcl3'),
                                             shortcutToCells.get('bbr3'),
                                             shortcutToCells.get('bi3')]
                            }

defaultShortcut = {'defaults': [ThreeVectorIntBlock(key='cell_constraints', lines=['0   0   0', '0   0   0']),
                                #StrBlock(key='species_pot', lines=['SOC19']),
                                BoolKeyword(key='fix_com', value=True),
                                StrKeyword(key='task', value='singlepoint'),
                                StrKeyword(key='xcfunctional', value='LDA'),
                                FloatKeyword(key='cut_off_energy', value=700.0, unit='eV'),
                                BoolKeyword(key='fix_occupancy', value=True),
                                IntKeyword(key='iprint', value=3)]
                   }

stringToSettings = shortcutToCells | shortcutToCellsAliases | shortcutToParams | shortcutToParamsAliases | defaultShortcut


def setting(key=None, *args, **kwargs):
    assert isinstance(key, str)

    key = key.strip().lower()

    settingObject = settingTypes.get(key, None)

    assert settingObject is not None, f'Key {key} does not correspond to setting'

    newSetting = settingObject(key, *args, **kwargs)

    return newSetting


def readSettings(file_=None):
    assert isinstance(file_, str)
    assert Path(file_).is_file(), f'Cannot find file {file_} when reading settings'

    with open(file_) as f:
        lines = f.read().splitlines()

    # Strip lines and ignore empty ones.
    lines = [line.strip() for line in lines if line.strip()]

    # Ignore whole line comments.
    lines = [line for line in lines if not line.startswith('#') and not line.startswith('!')]

    settingKey = ''  # What setting are we looking at?
    inBlock = False  # Are we in a block i.e. '%block species_pot'
    blockLines = []  # What are the lines of the block we are in?

    settings = []  # All the settings we are going to get...

    for line in lines:

        # Check for comment. This will go from left to right, so don't need to worry about multiple.
        comment = line.find('!')

        # Remove it if need be.
        if comment != -1:
            line = line[:comment].strip()

        # And do the same with the other comment flag.
        comment = line.find('#')

        # And remove.
        if comment != -1:
            line = line[:comment].strip()

        if inBlock:
            # Don't lower() line before as we may want capitalisation.
            if line.lower().startswith('%'):

                # Get rid of the '%' - don't need capitalisation now
                line = line[1:].strip().lower()

                # Check 'endblock' comes after.
                if line.startswith('endblock'):
                    line = line[8:].strip()

                    # Check that there is only one string after 'endblock'.
                    settingKeys = line.split()
                    if len(settingKeys) == 1:
                        settingKeyOther = settingKeys[0]
                    else:
                        raise ValueError(f'Error in block in line \'{line}\' of file {file_}')

                    assert settingKey == settingKeyOther, f'Entered block {settingKey} but found endblock {settingKeyOther}'

                    arguments = {'lines': blockLines}

                    newSetting = setting(key=settingKey, **arguments)

                    settings.append(newSetting)

                    # We have now exited a block.
                    inBlock = False
                    blockLines = []

                else:
                    raise ValueError(f'Error in block in line \'{line}\' of file {file_}')
            else:
                blockLines.append(line)

        else:
            # Don't lower() line before as we may want capitalisation if it is not a block.
            if line.lower().startswith('%'):

                # Get rid of the '%' - don't need capitalisation now
                line = line[1:].strip().lower()

                # Check 'block' comes after.
                if line.startswith('block'):
                    line = line[5:].strip()

                    # We have now entered a block.
                    inBlock = True
                    blockLines = []

                    # Check that there is only one string after 'block'.
                    settingKeys = line.split()
                    if len(settingKeys) == 1:
                        settingKey = settingKeys[0]
                    else:
                        raise ValueError(f'Error in block in line \'{line}\' of file {file_}')

                else:
                    raise ValueError(f'Error in block in line \'{line}\' of file {file_}')

            else:
                # If we're here then we have a keyword.

                parts = line.split()
                parts = [part.strip() for part in parts if part.strip() not in [':', '=']]

                if len(parts) == 1:
                    # e.g. symmetry_generate
                    key = parts[0].lower()
                    value = True

                    arguments = {'value': value}

                elif len(parts) == 2:
                    key = parts[0].lower()
                    value = stringToValue(parts[1])

                    arguments = {'value': value}

                elif len(parts) == 3:
                    key = parts[0].lower()
                    value = stringToValue(parts[1])
                    unit = parts[2]

                    arguments = {'value': value, 'unit': unit}

                elif len(parts) == 4:
                    # e.g. kpoints_mp_grid : 1 1 1
                    key = parts[0].lower()
                    value = stringToValue(' '.join(parts[1:]))

                    arguments = {'value': value}

                else:
                    raise ValueError(f'Error in keyword {line} of file {file_}')

                newSetting = setting(key=key, **arguments)

                settings.append(newSetting)

    return settings


def createSettings(*settings):
    """ This function takes in a list of strings and settings
        and converts the strings to the settings that they are
        shortcuts to """

    # Split the settings up into settings and shortcuts
    settings, shortcuts = parseArgs(*settings)

    # Check that we have one of each string.
    assertCount([shortcut.strip().lower() for shortcut in shortcuts])

    # The shortcuts point to one or more params/cells.
    # E.g. 'soc' is spin_treatment=vector and spin_orbit_coupling=true.
    settingsFromShortcuts = shortcutsToSettings(*shortcuts)

    assert all(isinstance(sttng, Setting) for sttng in settingsFromShortcuts), 'Type not recognised in shortcut'

    settings += settingsFromShortcuts

    # Check that none of the shortcuts themselves have now duplicated any cells/params.
    assertCount([sttng.key for sttng in settings])

    return settings


def createVariableSettings(*variableSettings):
    """ This functions takes in a list of strings/lists/tuples.
        The strings are treated as shortcuts and converted
        appropriately. The tuples are turned to lists. The
        output is a list of lists of settings. The list
        would then typically be outer producted to generate
        all the possible variations of the settings.
        E.g. [[HF, HCl], [soc=false, soc=true]]
        would be outer producted to
        [HF+soc=false, HF+soc=true, HCl+soc=false, HCl+soc=true] """

    processed = []

    for variable in variableSettings:
        assert isinstance(variable, (str, list, tuple)), \
            f'Specify only shortcut strings, lists or tuples for variable cells/params, not {type(variable)}'

        # Strings are shortcuts, but shortcuts to specific combinations of cells/params.
        # E.g. 'soc' is a tuple of three different settings:
        # 1 -> spin_treatment=scalar and spin_orbit_coupling=false
        # 2 -> spin_treatment=vector and spin_orbit_coupling=false
        # 3 -> spin_treatment=vector and spin_orbit_coupling=true
        # So let's turn the shortcut string (if needed) into its list combination.

        if isinstance(variable, str):
            variable = variable.strip().lower()

            found = stringToVariableSettings.get(variable, None)

            assert found is not None, f'Shortcut to variable settings {variable} not recognised'

            variable = found

        # Create a list to store this combination.
        lst = []

        for strListSetting in variable:
            # Shortcut string.
            if isinstance(strListSetting, str):
                variableSettings = shortcutsToSettings(strListSetting.strip().lower())
                lst.append(variableSettings)

            # User defined.
            elif isinstance(strListSetting, (list, tuple)):
                assert all(isinstance(sttng, Setting) for sttng in strListSetting), 'Settings should only be cells or params'
                lst.append(list(strListSetting))

            elif isinstance(strListSetting, Setting):
                lst.append([strListSetting])

            else:
                raise TypeError('A specific setting of several cells/params must be given as a shortcut or tuple')

        processed.append(lst)

    return processed


def shortcutsToSettings(*shortcuts):
    """ This function gets a specific shortcut from a string.
        A string maps to a list of cells/params and is simply
        an easy way to generate common settings in calculations. """

    settings = []

    for shortcut in shortcuts:
        assert isinstance(shortcut, str)

        settingOrList = stringToSettings.get(shortcut.lower(), None)

        newSettings = [settingOrList] if isinstance(settingOrList, Setting) else settingOrList

        assert newSettings is not None, f'Shortcut string {shortcut} not recognised'

        settings += newSettings

    return settings


def getCellsParams(settings=None):
    """ This functions takes a list of settings and
        splits them up into two sorted lists of
        cells and params"""

    if settings is None:
        return None

    assert isinstance(settings, list)
    assert all(isinstance(sttng, Setting) for sttng in settings)

    cells = []
    params = []

    for sttng in settings:
        if sttng.file == 'cell':
            cells.append(sttng)
        elif sttng.file == 'param':
            params.append(sttng)
        else:
            raise ValueError(f'File {sttng.file} not recognised')

    cells = sorted(cells, key=lambda cell: cell.priority)
    params = sorted(params, key=lambda param: param.priority)

    return cells, params


def parseArgs(*stringsAndSettings):
    """ This function takes in a list of settings
        and strings and splits them up into two
        lists """

    settings = []
    strings = []

    for arg in stringsAndSettings:
        if isinstance(arg, str):
            strings.append(arg)

        elif isinstance(arg, Setting):
            settings.append(arg)

        elif isinstance(arg, (list, tuple)):
            for arg2 in arg:
                if isinstance(arg2, str):
                    strings.append(arg2)

                elif isinstance(arg2, Setting):
                    settings.append(arg2)

                else:
                    raise TypeError(f'Cannot have type {type(arg2)} in iterable')

        else:
            raise TypeError(f'Cannot have type {type(arg)}')

    return settings, strings
