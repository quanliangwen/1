// Independent audit kernel: bounded exact signed128 sums, sorted-vector counts.
// No Python integer kernel, optimizer, native distribution, or cache is imported.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
using I=__int128_t; using U=__uint128_t;
const U LIMIT=(U(1)<<127)-1;
I parse(const std::string&s){
 bool neg=!s.empty()&&s[0]=='-';size_t k=neg?1:0;if(k==s.size())throw std::runtime_error("bad integer");U x=0;
 for(;k<s.size();++k){if(s[k]<'0'||s[k]>'9')throw std::runtime_error("bad digit");unsigned d=s[k]-'0';if(x>(LIMIT-d)/10)throw std::runtime_error("128-bit input overflow");x=x*10+d;}
 return neg?-I(x):I(x);
}
U abs128(I x){return x<0?U(-x):U(x);}
std::vector<I> sums(const std::vector<std::vector<I>>&samples,const std::vector<int>&ids){
 std::vector<I> result{0};for(int j:ids){if(result.size()>1000000/samples[j].size())throw std::runtime_error("half-state limit exceeded");std::vector<I> next;next.reserve(result.size()*samples[j].size());for(I x:result)for(I y:samples[j])next.push_back(x+y);result.swap(next);}return result;
}
int main(){
 try{
  std::ios::sync_with_stdio(false);std::cin.tie(nullptr);int models;if(!(std::cin>>models)||models<1||models>1000)throw std::runtime_error("bad model count");uint64_t all=0;
  for(int model=0;model<models;++model){
   int n,m;uint64_t queries;if(!(std::cin>>n>>m>>queries)||n<1||n>500||m<1||m>5||queries>500000)throw std::runtime_error("unsupported audit dimensions");
   std::vector<std::vector<I>>samples(n);U largest=0;
   for(auto&a:samples){int size;if(!(std::cin>>size)||size<1||size>1000)throw std::runtime_error("bad marginal size");for(int k=0;k<size;++k){std::string text;if(!(std::cin>>text))throw std::runtime_error("missing sample");I x=parse(text);largest=std::max(largest,abs128(x));a.push_back(x);}}
   if(largest>LIMIT/U(m+1))throw std::runtime_error("sum may overflow");
   std::map<std::vector<int>,std::vector<I>> leftCache,rightCache;
   for(uint64_t q=0;q<queries;++q){
    std::string threshold;uint64_t expected,expectedDen;if(!(std::cin>>threshold>>expected>>expectedDen))throw std::runtime_error("missing query");I T=parse(threshold);if(abs128(T)>LIMIT-largest*U(m))throw std::runtime_error("threshold difference may overflow");
    std::vector<int> choice(m);uint64_t den=1;for(int&j:choice){if(!(std::cin>>j)||j<0||j>=n)throw std::runtime_error("bad item ID");if(den>std::numeric_limits<uint64_t>::max()/samples[j].size())throw std::runtime_error("denominator overflow");den*=samples[j].size();}
    std::vector<int> l(choice.begin(),choice.begin()+m/2),r(choice.begin()+m/2,choice.end());
    if(!leftCache.count(l))leftCache[l]=sums(samples,l);
    if(!rightCache.count(r)){auto values=sums(samples,r);std::sort(values.begin(),values.end());rightCache[r]=std::move(values);}
    uint64_t num=0;const auto&right=rightCache[r];for(I x:leftCache[l]){auto position=std::lower_bound(right.begin(),right.end(),T-x);uint64_t count=position-right.begin();if(num>std::numeric_limits<uint64_t>::max()-count)throw std::runtime_error("numerator overflow");num+=count;}
    if(num!=expected||den!=expectedDen){std::cerr<<"COUNT_MISMATCH model="<<model<<" query="<<q<<" actual="<<num<<"/"<<den<<" expected="<<expected<<"/"<<expectedDen<<"\n";return 2;}
   }
   all+=queries;std::cout<<"MODEL_OK "<<model<<" "<<queries<<"\n";
  }
  std::string extra;if(std::cin>>extra)throw std::runtime_error("trailing input");std::cout<<"ALL_OK "<<models<<" "<<all<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
