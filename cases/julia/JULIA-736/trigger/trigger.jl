using Test
using Nemo

println("JULIA_TRIGGER_STARTED:JULIA-736")

@testset "JULIA-736 upstream MathConstants regression" begin
    # These assertions are copied from Nemo.jl PR #2104, which fixes issue #2099.
    # The issue reports loss of precision in AcbField conversion of Irrational constants.
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

println("JULIA_TRIGGER_COMPLETED:JULIA-736")
