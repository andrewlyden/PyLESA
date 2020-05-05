"""electrical storage model

module containing electrical storage class
with attributes for creating class and methods for
calculating charging, discharging, next state of charge,
losses
"""


class ElectricalStorage(object):

    def __init__(self, capacity, initial_state,
                 charge_max, discharge_max,
                 charge_eff, discharge_eff,
                 self_discharge):
        """initialises electrical storage class

        Arguments:
            capacity {float} -- capacity of storage in kWh
            initial_state {float} -- percentage of capacity
                                     stored in first timestep
            charge_max {float} -- maximum charge of storage kW
            discharge_max {float} -- maximum discharge of storage kW
            charge_eff {float} -- % of charging loss
            discharge_eff {float} -- % of discharging loss
            self_discharge {float} -- % of self-discharge in every timestep
        """

        self.capacity = capacity
        self.initial_state = initial_state
        self.charge_max = charge_max
        self.discharge_max = discharge_max
        self.charge_eff = charge_eff
        self.discharge_eff = discharge_eff
        self.self_discharge = self_discharge

    def init_state(self):
        i_s = self.initial_state * self.capacity
        return i_s

    def max_charging(self, match):
        """maximum electrical storage charging

        Arguments:
            match {float} -- difference between renewable generation and demand

        Returns:
            float -- maximum charge given excess renewable generation
                     does not account for available capacity hence maximum

        """
        # max possible charge
        max_p_charge = match * self.charge_eff

        if max_p_charge >= 0 and max_p_charge <= self.charge_max:
            max_charge = max_p_charge

        elif max_p_charge >= 0 and max_p_charge >= self.charge_max:
            max_charge = self.charge_max

        elif max_p_charge <= 0:
            max_charge = 0.0

        return max_charge

    def max_discharging(self, match):
        """maximum electrical storage discharging

        Arguments:
            match {float} -- difference between renewable generation and demand

        Returns:
            float -- maximum discharge given excess renewable generation
                     does not account for available capacity hence maximum
        """
        # max possible discharge
        max_p_dis = match * self.discharge_eff

        if max_p_dis < 0 and max_p_dis >= -1 * self.discharge_max:
            discharge = max_p_dis

        elif max_p_dis <= -1 * self.discharge_max:
            discharge = -1 * self.discharge_max

        elif max_p_dis >= 0:
            discharge = 0.0

        return discharge

    def self_loss(self, soc):
        """calculates self discharge in timestep

        Arguments:
            soc {float} -- state of charge at start of timestep

        Returns:
            float -- self-discharge in timestep
        """

        self_loss = soc * self.self_discharge

        return self_loss

    def new_soc(self, match, soc):
        """state of charge in new timestep

        Arguments:
            match {float} -- difference between renewable
                             generation and demand in timestep
            soc {float} -- state of charge at beginning of timestep

        Returns:
            float -- state of charge at end of timestep
        """

        # max new state of charge without considering capacity
        max_new_soc = (soc +
                       self.max_charging(match) +
                       self.max_discharging(match) -
                       self.self_loss(soc))

        # new soc considering capacity
        if max_new_soc >= self.capacity:
            next_soc = self.capacity

        elif max_new_soc <= 0:
            next_soc = 0

        else:
            next_soc = max_new_soc

        return next_soc

    def charging(self, match, soc):
        """charging after losses

        Arguments:
            match {float} -- difference between renewable generation and demand
            soc {float} -- state of charge at start of timestep

        Returns:
            float -- charging after losses
        """

        if match >= 0:
            charging = self.new_soc(match, soc) - soc

        elif match < 0:
            charging = 0

        return charging

    def discharging(self, match, soc):
        """discharging after losses

        Arguments:
            match {float} -- difference between renewable generation and demand
            soc {float} -- state of charge at start of timestep

        Returns:
            float -- discharging after losses
        """

        if match >= 0:
            discharging = 0

        elif match < 0:
            discharging = self.new_soc(match) - soc

        return discharging

    def charge_to_capacity(self, soc):
        """charging to full

        Arguments:
            soc {float} -- state of charge at start of timestep

        Returns:
            float -- maximum charge possible
        """    

        charging = self.capacity - soc
        losses = self.self_loss(soc) + charging * self.charge_eff
        total_charging = charging + losses
        return total_charging

    def total_losses(self, match, soc):
        """total losses in timestep

        calculates total losses in a timestep from self-discharge,
        and effieciencies when charging/max_discharging

        Arguments:
            match {float} -- difference between renewable generation
                             and demand in timestep
            soc {float} -- state of charge at start of timestep

        Returns:
            float -- total losses
        """

        losses = ((1 - self.charge_eff) * self.charging(match, soc) +
                  (1 - self.discharge_eff) * self.discharging(match, soc) -
                  self.self_loss(soc))

        return losses
