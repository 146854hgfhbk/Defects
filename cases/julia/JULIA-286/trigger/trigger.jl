using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "malformed strings" begin
    malformed = first("\xe2")
    @test JuliaSyntax.Tokenize.dotop1(malformed) == false
    @test JuliaSyntax.Tokenize.isopsuffix(malformed) == false
    @test JuliaSyntax.Tokenize.is_operator_start_char(malformed) == false
end
