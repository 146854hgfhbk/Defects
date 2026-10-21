using StaticArrays
println("JULIA-TRIGGER-START")
methods_for_size = collect(methods(size, (Type{SDiagonal{2,Float64}},)))
sig = string(first(methods_for_size).sig)
if occursin("<:", sig)
    error("SDiagonal size method still pirates a broad Diagonal type")
end
println("JULIA-586 trigger completed")
