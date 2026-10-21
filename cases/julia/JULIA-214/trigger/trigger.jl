println("JULIA-TRIGGER-START")
using Test
using IntervalArithmetic

@testset "JULIA-214 literal powers preserve guarantees" begin
    x = interval(-1, 1)
    @test isguaranteed(x ^ 2)
end
