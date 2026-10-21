println("JULIA-TRIGGER-START")
using Test
using Unitful
import Unitful: C, ms, s, V, m, kg, A

@testset "JULIA-720 compound preferred units" begin
    @test_logs (:warn, r"^Preferred units contain complex units") Unitful.preferunits(C / ms)
    Unitful.preferunits(C / s)
    @test Unitful.upreferred(V / m) == kg * m * C^-1 * s^-2
    @test Unitful.dimension(Unitful.upreferred(V / m)) == Unitful.dimension(V / m)
    Unitful.preferunits(A)
end
