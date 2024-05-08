import pylesa.storage.electrical_storage as electrical_storage
import pylesa.io.inputs as inputs


def battery_charge():

    i = inputs.electrical_storage()

    myElectricalStorage = electrical_storage.ElectricalStorage(
        i['capacity'],
        i['initial_state'],
        i['charge_max'],
        i['discharge_max'],
        i['charge_eff'],
        i['discharge_eff'],
        i['self_discharge'])

    match = 1500
    soc = myElectricalStorage.init_state()

    new_soc = myElectricalStorage.new_soc(match, soc)
    losses = myElectricalStorage.total_losses(match, soc)
    print(new_soc, 'new_soc')
    print(losses, 'losses')


battery_charge()
