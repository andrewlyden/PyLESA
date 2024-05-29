from pylesa.heat.models import Simple, PerformanceModel

class TestSimple:
    def test_hp_cop(self, ):
        cop = 4.
        duty = 5.
        model = Simple(cop, duty)
        assert isinstance(model, PerformanceModel)
        assert model.cop() == cop
        assert model.duty() == duty