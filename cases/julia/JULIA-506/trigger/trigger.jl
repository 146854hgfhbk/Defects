using Test
using JuliaSyntax
using JuliaSyntax: @K_str, kind
using JuliaSyntax.Tokenize: tokenize, untokenize

println("JULIA-TRIGGER-START")

function token_pairs(source)
    tokens = [untokenize(token, source) => kind(token) for token in tokenize(source)]
    @assert pop!(tokens) == ("" => K"EndMarker")
    return tokens
end

@testset "JULIA-506 CRLF comment token boundary" begin
    @test token_pairs("#\r\n") == ["#" => K"Comment", "\r\n" => K"NewlineWs"]
end
