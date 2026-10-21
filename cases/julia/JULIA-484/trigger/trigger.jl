using Test
using StatsFuns

println("JULIA-TRIGGER-START")

@testset "JULIA-484 finite gamma log density under scale underflow" begin
    @test StatsFuns.gammalogpdf(3.0, 1e-310, 1.0) == -Inf
end
