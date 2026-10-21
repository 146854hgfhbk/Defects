using Test
using Nemo

@testset "JULIA-736 upstream MathConstants regression" begin
    for RR in (ArbField(400),)
        @test overlaps(RR(MathConstants.pi), RR("3.141592653589793238462643 +/- 4.03e-25"))
        @test overlaps(RR(MathConstants.e), RR("2.718281828459045235360287 +/- 4.96e-25"))
        @test overlaps(RR(MathConstants.eulergamma), RR("0.5772156649015328606065121 +/- 3.42e-26"))
        @test overlaps(RR(MathConstants.catalan), RR("0.9159655941772190150546035 +/- 1.86e-26"))
        x = sin(RR(MathConstants.pi))
        @test contains(RR("0.0 +/- 8.40e-121"), x)
        @test contains(x, RR("0.0 +/- 8.40e-122"))
        x = log(RR(MathConstants.e))
        @test contains(RR("1.0 +/- 1.76e-120"), x)
        @test contains(x, RR("1.0 +/- 1.76e-121"))
    end
    set_precision!(Balls, 400) do
        RR = RealField()
        @test overlaps(RR(MathConstants.pi), RR("3.141592653589793238462643 +/- 4.03e-25"))
        @test overlaps(RR(MathConstants.e), RR("2.718281828459045235360287 +/- 4.96e-25"))
        @test overlaps(RR(MathConstants.eulergamma), RR("0.5772156649015328606065121 +/- 3.42e-26"))
        @test overlaps(RR(MathConstants.catalan), RR("0.9159655941772190150546035 +/- 1.86e-26"))
        x = sin(RR(MathConstants.pi))
        @test contains(RR("0.0 +/- 8.40e-121"), x)
        @test contains(x, RR("0.0 +/- 8.40e-122"))
        x = log(RR(MathConstants.e))
        @test contains(RR("1.0 +/- 1.76e-120"), x)
        @test contains(x, RR("1.0 +/- 1.76e-121"))
    end
    CC = AcbField(400)
    @test overlaps(CC(MathConstants.pi), CC("3.141592653589793238462643 +/- 4.03e-25"))
    @test overlaps(CC(MathConstants.e), CC("2.718281828459045235360287 +/- 4.96e-25"))
    @test overlaps(CC(MathConstants.eulergamma), CC("0.5772156649015328606065121 +/- 3.42e-26"))
    @test overlaps(CC(MathConstants.catalan), CC("0.9159655941772190150546035 +/- 1.86e-26"))
    x = sin(CC(MathConstants.pi))
    @test contains(CC("0.0 +/- 8.40e-121"), x)
    @test contains(x, CC("0.0 +/- 8.40e-122"))
    x = log(CC(MathConstants.e))
    @test contains(CC("1.0 +/- 1.76e-120"), x)
    @test contains(x, CC("1.0 +/- 1.76e-121"))
end
