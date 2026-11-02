// Compile-time check for the unverified benchmark's Rust FFI declarations.
#include <gmp.h>
#include <cstdint>
#include <iostream>
#include <type_traits>
static_assert(GMP_NUMB_BITS==64 && GMP_NAIL_BITS==0);
static_assert(sizeof(mp_limb_t)==sizeof(uint64_t) && std::is_unsigned<mp_limb_t>::value);
static_assert(sizeof(mp_size_t)==sizeof(intptr_t) && std::is_signed<mp_size_t>::value);
int main(){
    std::cout << "GMP runtime " << gmp_version << "; header "
        << __GNU_MP_VERSION << '.' << __GNU_MP_VERSION_MINOR << '.' << __GNU_MP_VERSION_PATCHLEVEL
        << "; C++ compiler " << __VERSION__ << '\n';
}
