using Test
using BasicBSpline

println("JULIA-TRIGGER-START")

@testset "JULIA-197 signed-zero knot counting" begin
    knots = KnotVector([-2.0, -1.0, -0.0, -0.0, 0.0, 1.0, 3.0])
    @test countknots(knots, 0) == 3
    @test countknots(knots, 0.0) == 3
    @test countknots(knots, -0.0) == 3
end
