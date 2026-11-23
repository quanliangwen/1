// Independent post-run integer polynomial reader. Never links to solver objects.
#include <gmpxx.h>
#include <iostream>
#include <stdexcept>
int main() {
    try {
        unsigned long width,cut,factors;
        if (!(std::cin>>width>>cut>>factors)) return 2;
        if (!width||width>4096||!cut||cut>1048576||!factors||factors>1000) return 3;
        mpz_class product=1;
        for (unsigned long k=0;k<factors;++k) {
            unsigned long entries;std::cin>>entries;
            mpz_class factor=0;
            for (unsigned long i=0;i<entries;++i) {
                unsigned long degree,count;std::cin>>degree>>count;
                if (degree>=cut) return 4;
                unsigned long bit=0;
                while(count) {
                    if(count&1UL)mpz_setbit(factor.get_mpz_t(),width*degree+bit);
                    count>>=1;++bit;
                }
                if(bit>width)return 5;
            }
            product*=factor;
            mpz_fdiv_r_2exp(product.get_mpz_t(),product.get_mpz_t(),width*cut);
        }
        mpz_class modulus;
        mpz_ui_pow_ui(modulus.get_mpz_t(),2,width);
        modulus-=1;
        mpz_class numerator=product%modulus;
        std::cout<<numerator.get_str()<<'\n';
        return std::cin.fail()?6:0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
