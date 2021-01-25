import re
from decimal import Decimal

exact_masses = {'He': 4.002603,
                'Li': 7.016005,
                'Be': 9.012183,
                'B': 11.009305,
                'F': 18.998403,
                'Mg': 23.985042,
                'Al': 26.981541,
                'Si': 27.976928,
                'Cl': 34.968853,
                'Fe': 55.934942,
                'Cu': 62.929601,
                'Co': 58.933200,
                'Ni': 57.935348,
                'Zn': 63.929145,
                'Br': 78.918336,
                'C': 12.0,
                'O': 15.994915,
                'H': 1.007825,
                'N': 14.003074,
                'P': 30.973762,
                'S': 31.972071,
                'K': 38.963707,
                'Na': 22.989770,
                'Ca': 39.962591}


def get_element_dict(formula):
    elements = {}
    matches = re.findall(r'[A-Z][a-z]?[0-9]*', formula)
    if len("".join(matches)) != len(formula):
        return 'invalid formula'
    for m in matches:
        result = re.search(r'(\D+)(\d*)', m)
        if result[1] not in exact_masses:
            return 'invalid formula'
        if result[1] in elements:
            elements[result[1]] += int(result[2]) if result[2] != '' else 1
        else:
            elements[result[1]] = int(result[2]) if result[2] != '' else 1
        
    return elements

def get_formula_from_dict(elements):
    formula = ''
    for key, value in elements.items():
        if value == 1:
            formula += key
        else:
            formula += key + str(value)
    return formula

class Compound():
    def __init__(self, formula, name = None, charge = 0, adduct = None):
        self.formula = formula
        self.elements = get_element_dict(formula)
        self.name = name
        self.charge = charge
        self.adduct = adduct

    def calc_mass(self, round_by=4):
        mass = Decimal('0')
        if self.charge < 0 and 'H' not in self.elements:
            raise Exception(f'Can not measure mass in negative mode if no H in formula!', AttributeError)
        for key, value in self.elements.items():
            mass += Decimal(str(exact_masses[key])) * value
        if self.charge != 0:
            mass -= Decimal('0.000549') * self.charge
        if self.charge == 1:
            if self.adduct != '':
                mass = mass + Decimal(str(exact_masses[self.adduct]))
            else:
                mass = mass + Decimal(str(exact_masses['H']))
        elif self.charge > 1:
            if self.adduct != '':
                mass = (mass+self.charge*Decimal(str(exact_masses[self.adduct])))/self.charge
            else:
                mass = (mass+self.charge*Decimal(str(exact_masses['H'])))/self.charge
        elif self.charge == -1:
            print(mass)
            mass = mass - Decimal(str(exact_masses['H']))
            print(mass)
        elif self.charge < -1:
            mass = (mass+self.charge*Decimal(str(exact_masses['H'])))/(self.charge* -1)
        return round(mass, round_by)
    
    def add_elements(self, add):
        to_add = get_element_dict(add)
        for key, value in to_add.items():
            if key in self.elements.keys():
                self.elements[key] += value
            else:
                self.elements[key] = value
        self.formula = get_formula_from_dict(self.elements)
        return self

    def del_elements(self, delete):
        to_delete = get_element_dict(delete)
        for key, value in to_delete.items():
            if key not in self.elements.keys():
                return f'Can not delete, {key} not in formula!'
            elif value > self.elements[key]:
                raise Exception(f'Can not delete, less of {value} {key} in {self.formula}!', ValueError)
                #return f'Can not delete, less of {value} {key} in {self.formula}!'
        for key, value in to_delete.items():
            self.elements[key] -= value
            if self.elements[key] == 0:
                del self.elements[key]
        self.formula = get_formula_from_dict(self.elements)
        return self
    
    def change_name(self, name):
        self.name = name
        return self

    def check_formula(self):
        if re.search(r'[0-9]+[a-z]+',self.formula) or re.search(r'^[a-z]+',self.formula) or re.search(r'[A-Z][a-z]{2,}',self.formula) or re.search(r'^[0-9]+',self.formula):
            return False
        for char in self.formula:
            if not char.isalnum():
                return False
        for key in self.elements.keys():
            try:
                check = exact_masses[key]
            except KeyError:
                return False
        return True
            
    def copy(self):
        return Compound(self.formula, self.name)
    
    def add_compound(self, compound, elimination = 'H2O', name='New Added Compound'):
        new_compound = self.copy()
        new_compound.name = name
        new_compound.add_elements(compound.formula)
        new_compound.del_elements(elimination)
        return new_compound
    
    def del_compound(self, compound, elimination = 'H2O', name='New Added Compound'):
        new_compound = self.copy()
        new_compound.name = name
        new_compound.del_elements(compound.formula)
        new_compound.add_elements(elimination)
        return new_compound
    
    def multiply(self, multiply, name='New Multiplied Compound', elimination = 'H2O'):
        new_compound = self.copy()
        new_compound.name = name
        new_formula = self.formula * multiply
        new_compound.elements = get_element_dict(new_formula)
        new_compound.formula = get_formula_from_dict(new_compound.elements)
        new_compound.del_elements(elimination*(multiply-1))
        return new_compound