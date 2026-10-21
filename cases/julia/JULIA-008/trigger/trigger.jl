println("JULIA-TRIGGER-START")
using Test
using CSV

@testset "JULIA-008 decimal comma delimiter detection" begin
    table = CSV.File(IOBuffer("a;b;c\n1,1;2,2;3,3\n4,4;5,5;6,6\n"); decimal=',')
    @test (length(table), length(table.names)) == (2, 3)
    @test table.a == [1.1, 4.4]
    @test table.b == [2.2, 5.5]
    @test table.c == [3.3, 6.6]
end
