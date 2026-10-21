println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

@testset "JULIA-083 incomplete let comment" begin
    input = "let x = 1 # comment"
    statement = JuliaSyntax.core_parser_hook(input, "somefile", 1, 0, :statement)[1]
    @test Base.incomplete_tag(statement) == :other
    complete = JuliaSyntax.core_parser_hook(input, "somefile", 1, 0, :all)[1]
    @test complete.head == :toplevel
    @test Base.incomplete_tag(complete.args[end]) == :other
end
println("JULIA-083 trigger completed")
