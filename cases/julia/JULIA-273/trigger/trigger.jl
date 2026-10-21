println("JULIA-TRIGGER-START")
using Test
using Runic: format_string

@testset "JULIA-273 anonymous function spacing" begin
    for space in ("", " ")
        @test format_string("function$(space)(::Type{T})(::Int) where {T}\n$(space)return T\n$(space)end") ==
            "function (::Type{T})(::Int) where {T}\n    return T\nend"
        @test format_string("function$(space)()() end") == "function ()() end"
    end
end
