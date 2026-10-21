println("JULIA-TRIGGER-START")
using Test
using Runic

@testset "JULIA-283 tuple destructuring trailing comma" begin
    source = "x, = (1, 2, 3)"
    @test Runic.format_string(source) == source
end
