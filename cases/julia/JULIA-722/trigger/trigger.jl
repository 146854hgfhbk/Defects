using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "SourceFile lines and column indexing" begin
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("a\nb\n"), 2) == (1, 2)
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("a\nb\n"), 3) == (2, 1)
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("a\nb\n"), 5) == (2, 3)
end
