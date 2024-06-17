from pylesa.heat.models import Simple, PerformanceModel


class TestSimple:
    def test_hp_cop(
        self,
    ):
        cop = 4.0
        duty = 5.0
        model = Simple(cop, duty)
        assert isinstance(model, PerformanceModel)
        assert model.cop() == cop
        assert model.duty() == duty
