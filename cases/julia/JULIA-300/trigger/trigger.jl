println("JULIA-TRIGGER-START")
using Test
using JuliaFormatter

@testset "JULIA-300 preserves standalone block comments" begin
    source = "#= this is a valuable comment =#"
    @test occursin("this is a valuable comment", JuliaFormatter.format_text(source))
end
