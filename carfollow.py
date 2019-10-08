""" 
    Car following model
"""

# ===============================================================================
# Imports
# ===============================================================================

import numpy as np
from math import sqrt
from typing import Union
from vehicles import Vehicle, DT, K_X, W_I, U_I

# ===============================================================================
# Constants
# ===============================================================================

T_E = 0.2
S_0 = 1 / K_X

# TAMPERE MODEL
C_1 = 0.5  # Speed difference coefficient
C_2 = 0.5  # Spacing coefficient
C_3 = 0.5  # Tampere coefficient

# IDM MODEL
B = 1.5
DELTA = 4
V_0 = 25  # 90 / 3.6

# ===============================================================================
# Clases
# ===============================================================================


class CarFollowLaw(Vehicle):
    """
        Generic Car Following Behavior
    """

    def __init__(self, x0: float, v0: float, veh_lead=None, behavior: str = None) -> None:
        super().__init__(x0, v0, veh_lead)
        self.behavior = behavior

    @property
    def u(self) -> float:
        """
            Free flow speed
        """
        return U_I

    @property
    def w(self) -> float:
        """
            Shockwave speed
        """
        return W_I

    @property
    def k_x(self) -> float:
        """
            Jam density
        """
        return K_X

    @property
    def s0(self) -> float:
        """
            Minimum spacing
        """
        return 1 / self.k_x

    @property
    def vl(self) -> float:
        """
            Leader speed 
        """
        return self.veh_lead.v_t

    @property
    def dv(self) -> float:
        """ 
            Determine current delta of speed
        """
        if self.veh_lead:
            return self.vl - self.v_t
        return 0

    @property
    def xl(self) -> float:
        """
            Leader position
        """
        return self.veh_lead.x_t

    @property
    def s(self) -> float:
        """
            Determine current spacing (X_n-1 - X_n)
        """
        if self.veh_lead:
            return self.xl - self.x_t
        return 0

    @property
    def T(self) -> float:
        """
            Reaction time
        """
        return DT

    def step_evolution(self, v_d: float, control: float = 0) -> None:
        """
            Use this method to a single step in the simulation
        """
        self.shift_state()  # x_{k-1} = x{k} move info from last time step into current
        self.control = control  # Update control
        self.car_following(v_d)  # Update acceleration


# IDM Car Following Model


class IDM(CarFollowLaw):
    """
        Intelligent Driver's Model Car Following 
    """

    __slots__ = ["_b", "_delta", "_v0"]

    def __init__(self, x0: float, v0: float, veh_lead=None) -> None:
        super().__init__(x0, v0, veh_lead, self.__class__.__name__)

    @property
    def b(self) -> float:
        """
            Comfortable decceleration
        """
        return B

    @b.setter
    def b(self, value: float = B) -> None:
        self._b = value

    @property
    def delta(self) -> float:
        """
            Acceleration exponent 
        """
        return self._delta

    @delta.setter
    def delta(self, value: float = DELTA) -> None:
        self._delta = value

    @property
    def v0(self) -> float:
        """
            Desired speed
        """
        return self._v0

    @v0.setter
    def v0(self, value: float = V_0) -> float:
        self._v0 = value

    def s_star(self) -> float:
        """
            Desired spacing 
        """
        return self.s0 + max(0, self.v * self.T + (self.v * self.dv) / (2 * sqrt(self.a * self.b)))

    def acel(self, vd) -> float:

        return self.a * (1 - (self.v / self.v0) ** self.delta - (self.s_star() / self.s) ** 2)

    def car_following(self, vd: float) -> None:
        """ 
            Acceleration car following 
            
            Note: 
                if leader 
                    min(cong_acc, free_acc) -> Tampere
                else 
                    manual acceleration
        """
        if self.veh_lead:
            self.a = self.acel(vd)  # Car following
        else:
            self.a = self.control  # Leader vehicle 2nd order


# Tampere Car Following Model


class Tampere(CarFollowLaw):
    """
        Tampere Car Following Model
    """

    __slots__ = ["_c1", "_c2", "_c3"]

    def __init__(self, x0: float, v0: float, veh_lead=None, **kwargs) -> None:
        super().__init__(x0, v0, veh_lead, self.__class__.__name__)
        self.set_parameters(**kwargs)

    @property
    def c1(self) -> float:
        """
            Speed difference coefficient
        """
        return self._c1

    @property
    def c2(self) -> float:
        """
            Spacing coefficient
        """
        return self._c2

    @property
    def c3(self) -> float:
        """        
            Tampere coefficient
        """
        return self._c3

    @c1.setter
    def c1(self, value: float = C_1) -> None:
        self._c1 = value

    @c2.setter
    def c2(self, value: float = C_2) -> None:
        self._c2 = value

    @c3.setter
    def c3(self, value: float = C_3) -> None:
        self._c3 = value

    def set_parameters(self, c1=C_1, c2=C_2, c3=C_3) -> None:
        """
            Set default parameters
        """
        self.c1 = c1
        self.c2 = c2
        self.c3 = c3

    @property
    def s_d(self) -> float:
        """
            Determine desired spacing  (d + gamma * v )
        """
        return self.s0 + 1 / (self.w * self.k_x) * self.v

    def cong_acc(self) -> float:
        """
            Breaking term  c_1 (D V) + c_2 (s - s_d)
        """
        return self.c1 * self.dv + self.c2 * (self.s - self.s_d)

    def free_acc(self, vd: float = U_I) -> float:
        """
            Acceleration term (Tampere) c_3 (v_d - v)
        """
        return self.c3 * (vd - self.v_t)

    def acel(self, vd) -> float:
        """
            Acceleration term 
        """
        return min(self.cong_acc(), self.free_acc(vd))

    def car_following(self, vd: float) -> None:
        """ 
            Acceleration car following 
            
            Note: 
                if leader 
                    min(cong_acc, free_acc) -> Tampere
                else 
                    manual acceleration
        """
        if self.veh_lead:
            self.a = self.acel(vd)  # Car following
        else:
            self.a = self.control  # Leader vehicle 2nd order
