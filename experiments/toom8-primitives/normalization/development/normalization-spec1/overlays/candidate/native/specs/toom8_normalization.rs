//! Endpoint removal and exact homogeneous normalization, independent of outputs.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::radix_add;
use crate::toom8_dyadic_producer_spec::{power,product_weights};
use crate::toom8_convolution as convolution;
use crate::toom8_newton_spec as newton;
verus! {
pub open spec fn nonnegative(c:Seq<int>)->bool {c.len()==15 && forall|j:int|0<=j<15 ==> #[trigger] c[j]>=0}
pub open spec fn bounded(c:Seq<int>,r:int)->bool {r>0 && c.len()==15 && forall|j:int|0<=j<15 ==> 0<=#[trigger] c[j]<8*r*r}
pub open spec fn exponent(node:u32)->u32 {if node==0 {3}else if node==1 {2}else if node==2 {1}else if node==3 {0}else if node==4 {1}else{2}}
pub open spec fn reciprocal(node:u32)->bool {node<3}
pub open spec fn point(node:u32)->int {if node==0 {1}else if node==1 {4}else if node==2 {16}else if node==3 {64}else if node==4 {256}else{1024}}
pub open spec fn even_coefficients(c:Seq<int>)->Seq<int> recommends c.len()==15 {seq![c[2],c[4],c[6],c[8],c[10],c[12],0]}
pub open spec fn odd_coefficients(c:Seq<int>)->Seq<int> recommends c.len()==15 {seq![c[1],c[3],c[5],c[7],c[9],c[11],c[13]]}
pub open spec fn raw_even(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {convolution::even_value(c,product_weights(exponent(node),reciprocal(node)))}
pub open spec fn raw_odd(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {convolution::odd_value(c,product_weights(exponent(node),reciprocal(node)))}
pub open spec fn low_multiplier(node:u32)->int {if node==0 {4398046511104} else if node==1 {268435456} else if node==2 {16384} else if node==3 {1} else if node==4 {1} else {1}}
pub open spec fn high_multiplier(node:u32)->int {if node==0 {1} else if node==1 {1} else if node==2 {1} else if node==3 {1} else if node==4 {16384} else {268435456}}
pub open spec fn even_divisor(node:u32)->int {if node==0 {64} else if node==1 {16} else if node==2 {4} else if node==3 {1} else if node==4 {4} else {16}}
pub open spec fn odd_divisor(node:u32)->int {if node==0 {8} else if node==1 {4} else if node==2 {2} else if node==3 {1} else if node==4 {2} else {4}}
pub open spec fn even_scale(node:u32)->int {if node==0 {1} else if node==1 {1024} else if node==2 {1048576} else if node==3 {1073741824} else if node==4 {1073741824} else {1073741824}}
pub open spec fn odd_scale(node:u32)->int {if node==0 {1} else if node==1 {4096} else if node==2 {16777216} else if node==3 {68719476736} else if node==4 {68719476736} else {68719476736}}
pub open spec fn even_quotient(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {if node==0 {1073741824int*c[2]+16777216int*c[4]+262144int*c[6]+4096int*c[8]+64int*c[10]+1int*c[12]} else if node==1 {1048576int*c[2]+65536int*c[4]+4096int*c[6]+256int*c[8]+16int*c[10]+1int*c[12]} else if node==2 {1024int*c[2]+256int*c[4]+64int*c[6]+16int*c[8]+4int*c[10]+1int*c[12]} else if node==3 {1int*c[2]+1int*c[4]+1int*c[6]+1int*c[8]+1int*c[10]+1int*c[12]} else if node==4 {1int*c[2]+4int*c[4]+16int*c[6]+64int*c[8]+256int*c[10]+1024int*c[12]} else {1int*c[2]+16int*c[4]+256int*c[6]+4096int*c[8]+65536int*c[10]+1048576int*c[12]}}
pub open spec fn odd_quotient(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {if node==0 {68719476736int*c[1]+1073741824int*c[3]+16777216int*c[5]+262144int*c[7]+4096int*c[9]+64int*c[11]+1int*c[13]} else if node==1 {16777216int*c[1]+1048576int*c[3]+65536int*c[5]+4096int*c[7]+256int*c[9]+16int*c[11]+1int*c[13]} else if node==2 {4096int*c[1]+1024int*c[3]+256int*c[5]+64int*c[7]+16int*c[9]+4int*c[11]+1int*c[13]} else if node==3 {1int*c[1]+1int*c[3]+1int*c[5]+1int*c[7]+1int*c[9]+1int*c[11]+1int*c[13]} else if node==4 {1int*c[1]+4int*c[3]+16int*c[5]+64int*c[7]+256int*c[9]+1024int*c[11]+4096int*c[13]} else {1int*c[1]+16int*c[3]+256int*c[5]+4096int*c[7]+65536int*c[9]+1048576int*c[11]+16777216int*c[13]}}
pub open spec fn normalized_even(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {if node==0 {1073741824int*c[2]+16777216int*c[4]+262144int*c[6]+4096int*c[8]+64int*c[10]+1int*c[12]} else if node==1 {1073741824int*c[2]+67108864int*c[4]+4194304int*c[6]+262144int*c[8]+16384int*c[10]+1024int*c[12]} else if node==2 {1073741824int*c[2]+268435456int*c[4]+67108864int*c[6]+16777216int*c[8]+4194304int*c[10]+1048576int*c[12]} else if node==3 {1073741824int*c[2]+1073741824int*c[4]+1073741824int*c[6]+1073741824int*c[8]+1073741824int*c[10]+1073741824int*c[12]} else if node==4 {1073741824int*c[2]+4294967296int*c[4]+17179869184int*c[6]+68719476736int*c[8]+274877906944int*c[10]+1099511627776int*c[12]} else {1073741824int*c[2]+17179869184int*c[4]+274877906944int*c[6]+4398046511104int*c[8]+70368744177664int*c[10]+1125899906842624int*c[12]}}
pub open spec fn normalized_odd(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {if node==0 {68719476736int*c[1]+1073741824int*c[3]+16777216int*c[5]+262144int*c[7]+4096int*c[9]+64int*c[11]+1int*c[13]} else if node==1 {68719476736int*c[1]+4294967296int*c[3]+268435456int*c[5]+16777216int*c[7]+1048576int*c[9]+65536int*c[11]+4096int*c[13]} else if node==2 {68719476736int*c[1]+17179869184int*c[3]+4294967296int*c[5]+1073741824int*c[7]+268435456int*c[9]+67108864int*c[11]+16777216int*c[13]} else if node==3 {68719476736int*c[1]+68719476736int*c[3]+68719476736int*c[5]+68719476736int*c[7]+68719476736int*c[9]+68719476736int*c[11]+68719476736int*c[13]} else if node==4 {68719476736int*c[1]+274877906944int*c[3]+1099511627776int*c[5]+4398046511104int*c[7]+17592186044416int*c[9]+70368744177664int*c[11]+281474976710656int*c[13]} else {68719476736int*c[1]+1099511627776int*c[3]+17592186044416int*c[5]+281474976710656int*c[7]+4503599627370496int*c[9]+72057594037927936int*c[11]+1152921504606846976int*c[13]}}

pub proof fn relations(c:Seq<int>,node:u32)
    requires nonnegative(c),node<6,
    ensures raw_even(c,node)==low_multiplier(node)*c[0]+high_multiplier(node)*c[14]+even_divisor(node)*even_quotient(c,node),
        raw_odd(c,node)==odd_divisor(node)*odd_quotient(c,node),
        normalized_even(c,node)==even_scale(node)*even_quotient(c,node),
        normalized_odd(c,node)==odd_scale(node)*odd_quotient(c,node),
        even_quotient(c,node)>=0,odd_quotient(c,node)>=0,
        low_multiplier(node)>0,high_multiplier(node)>0,even_divisor(node)>0,odd_divisor(node)>0,
        even_scale(node)>0,odd_scale(node)>0,
        newton::nonnegative(even_coefficients(c)),newton::nonnegative(odd_coefficients(c)),
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0 && c[7]>=0 && c[8]>=0 && c[9]>=0 && c[10]>=0 && c[11]>=0 && c[12]>=0 && c[13]>=0 && c[14]>=0);
    reveal_with_fuel(power,15);
    if node==0 {}else if node==1 {}else if node==2 {}else if node==3 {}else if node==4 {}else {assert(node==5);}
    assert forall|j:int|0<=j<7 implies #[trigger] even_coefficients(c)[j]>=0 by {if j==0 {}else if j==1 {}else if j==2 {}else if j==3 {}else if j==4 {}else if j==5 {}else {assert(j==6);}}
    assert forall|j:int|0<=j<7 implies #[trigger] odd_coefficients(c)[j]>=0 by {if j==0 {}else if j==1 {}else if j==2 {}else if j==3 {}else if j==4 {}else if j==5 {}else {assert(j==6);}}
}
pub proof fn normalization_capacity(c:Seq<int>,node:u32,k:nat)
    requires bounded(c,radix(k)),node<6,
    ensures normalized_even(c,node)<radix(2*(k+1)),normalized_odd(c,node)<radix(2*(k+1)),
{
    let r=radix(k);let bound=8*r*r;
    assert(c[0]<bound && c[1]<bound && c[2]<bound && c[3]<bound && c[4]<bound && c[5]<bound && c[6]<bound && c[7]<bound && c[8]<bound && c[9]<bound && c[10]<bound && c[11]<bound && c[12]<bound && c[13]<bound && c[14]<bound);
    if node==0 {}else if node==1 {}else if node==2 {}else if node==3 {}else if node==4 {}else {assert(node==5);}
    assert(normalized_even(c,node)<37778931862957161709568int*bound);
    assert(normalized_odd(c,node)<37778931862957161709568int*bound);
    radix_add(k+1,k+1);radix_positive(k);
    assert(radix(2*(k+1))==340282366920938463463374607431768211456int*r*r) by(nonlinear_arith)
        requires radix(k+1)==18446744073709551616int*r,radix(2*(k+1))==radix(k+1)*radix(k+1);
    assert(normalized_even(c,node)<radix(2*(k+1)) && normalized_odd(c,node)<radix(2*(k+1))) by(nonlinear_arith)
        requires r>0,bound==8*r*r,normalized_even(c,node)<37778931862957161709568int*bound,normalized_odd(c,node)<37778931862957161709568int*bound,
            radix(2*(k+1))==340282366920938463463374607431768211456int*r*r;
}
pub proof fn newton_node_0(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,0)==newton::even_state_0_0(even_coefficients(c)),
        normalized_odd(c,0)==newton::odd_state_0_0(odd_coefficients(c)),
{
    reveal(newton::even_state_0_0);reveal(newton::odd_state_0_0);
}
pub proof fn newton_node_1(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,1)==newton::even_state_0_1(even_coefficients(c)),
        normalized_odd(c,1)==newton::odd_state_0_1(odd_coefficients(c)),
{
    reveal(newton::even_state_0_1);reveal(newton::odd_state_0_1);
}
pub proof fn newton_node_2(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,2)==newton::even_state_0_2(even_coefficients(c)),
        normalized_odd(c,2)==newton::odd_state_0_2(odd_coefficients(c)),
{
    reveal(newton::even_state_0_2);reveal(newton::odd_state_0_2);
}
pub proof fn newton_node_3(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,3)==newton::even_state_0_3(even_coefficients(c)),
        normalized_odd(c,3)==newton::odd_state_0_3(odd_coefficients(c)),
{
    reveal(newton::even_state_0_3);reveal(newton::odd_state_0_3);
}
pub proof fn newton_node_4(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,4)==newton::even_state_0_4(even_coefficients(c)),
        normalized_odd(c,4)==newton::odd_state_0_4(odd_coefficients(c)),
{
    reveal(newton::even_state_0_4);reveal(newton::odd_state_0_4);
}
pub proof fn newton_node_5(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,5)==newton::even_state_0_5(even_coefficients(c)),
        normalized_odd(c,5)==newton::odd_state_0_5(odd_coefficients(c)),
{
    reveal(newton::even_state_0_5);reveal(newton::odd_state_0_5);
}
}
