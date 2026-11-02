// Unverified independent comparator. Not linked into the verified Rust backend.
// mpn_mul_n computes 2n limbs; copy/truncate/mask gives the same output contract.
#include <gmp.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

static_assert(GMP_NUMB_BITS == 64 && sizeof(mp_limb_t) == 8);

static void product(std::vector<mp_limb_t>& out, std::vector<mp_limb_t>& scratch,
                    const std::vector<mp_limb_t>& a, const std::vector<mp_limb_t>& b, unsigned top) {
    if (a.empty() || a.size()!=b.size() || out.size()!=a.size() || top<1 || top>64)
        throw std::invalid_argument("modular product shape");
    mpn_mul_n(scratch.data(),a.data(),b.data(),a.size());
    std::copy_n(scratch.data(),out.size(),out.data());
    if (top<64) out.back() &= (mp_limb_t{1} << top)-1;
}

static uint64_t rotate(uint64_t x, unsigned r) { return (x<<r) | (x>>(64-r)); }

int main(int argc, char** argv) {
    if (argc==2 && std::string(argv[1])=="--version") { std::cout<<gmp_version<<'\n'; return 0; }
    if (argc==3 && std::string(argv[1])=="--bench") {
        uint64_t seed=std::stoull(argv[2]);
        std::cout<<"limbs,top,repetition,iterations,gmp_ns\n";
        for (auto [n,top] : std::vector<std::pair<size_t,unsigned>>{{1,63},{1,64},{2,1},{2,63},{2,64},
                {4,63},{8,63},{16,63},{32,63},{64,63},{128,63},{256,63},{512,63},{1024,63}}) {
            std::vector<mp_limb_t> a(n),b(n),out(n),scratch(2*n);
            for (size_t i=0;i<n;++i) { a[i]=rotate(seed*(i+1),23); b[i]=rotate(seed+i,37); }
            auto batch=[&](uint64_t count) {
                auto start=std::chrono::steady_clock::now();
                for (uint64_t i=0;i<count;++i) {
                    asm volatile("" : : "g"(a.data()), "g"(b.data()), "g"(out.data()) : "memory");
                    product(out,scratch,a,b,top);
                    asm volatile("" : : "g"(out.data()) : "memory");
                }
                return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
            };
            uint64_t count=1;
            while (batch(count)<30'000'000 && count<(uint64_t{1}<<30)) count*=2;
            for (int rep=0;rep<7;++rep)
                std::cout<<n<<','<<top<<','<<rep<<','<<count<<','<<batch(count)<<'\n';
        }
        return 0;
    }
    size_t n; unsigned top;
    while (std::cin>>n>>top) {
        std::vector<mp_limb_t> a(n),b(n),out(n),scratch(2*n);
        for (auto& x:a) if (!(std::cin>>x)) return 2;
        for (auto& x:b) if (!(std::cin>>x)) return 2;
        product(out,scratch,a,b,top);
        for (size_t i=0;i<n;++i) std::cout<<(i ? " " : "")<<out[i];
        std::cout<<'\n';
    }
}
