//! Ghost-only fixed-node Newton identities; no runtime matrix kernel.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
verus! {
pub open spec fn nonnegative(c:Seq<int>)->bool {c.len()==7 && forall|i:int| 0<=i<7 ==> #[trigger] c[i]>=0}
pub open spec fn mass(c:Seq<int>)->int recommends c.len()==7 {c[0]+c[1]+c[2]+c[3]+c[4]+c[5]+c[6]}
pub open spec fn even_difference_1_5_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+17179869184int*c[1]+274877906944int*c[2]+4398046511104int*c[3]+70368744177664int*c[4]+1125899906842624int*c[5]}
pub open spec fn even_difference_1_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+4294967296int*c[1]+17179869184int*c[2]+68719476736int*c[3]+274877906944int*c[4]+1099511627776int*c[5]}
pub open spec fn even_difference_1_5_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+335544320int*c[2]+5637144576int*c[3]+91268055040int*c[4]+1464583847936int*c[5]}
pub proof fn even_difference_1_5(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_1_5_before(c)==1int*even_difference_1_5_rhs(c)+768int*even_difference_1_5_after(c),
        even_difference_1_5_before(c)>=1int*even_difference_1_5_rhs(c),
        0<=even_difference_1_5_after(c)<=1464583847936int*mass(c),
        (even_difference_1_5_before(c)-1int*even_difference_1_5_rhs(c))%768int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_1_5_after(c),768int);
}
pub open spec fn even_difference_1_4_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+4294967296int*c[1]+17179869184int*c[2]+68719476736int*c[3]+274877906944int*c[4]+1099511627776int*c[5]}
pub open spec fn even_difference_1_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+1073741824int*c[1]+1073741824int*c[2]+1073741824int*c[3]+1073741824int*c[4]+1073741824int*c[5]}
pub open spec fn even_difference_1_4_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+83886080int*c[2]+352321536int*c[3]+1426063360int*c[4]+5721030656int*c[5]}
pub proof fn even_difference_1_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_1_4_before(c)==1int*even_difference_1_4_rhs(c)+192int*even_difference_1_4_after(c),
        even_difference_1_4_before(c)>=1int*even_difference_1_4_rhs(c),
        0<=even_difference_1_4_after(c)<=5721030656int*mass(c),
        (even_difference_1_4_before(c)-1int*even_difference_1_4_rhs(c))%192int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_1_4_after(c),192int);
}
pub open spec fn even_difference_1_3_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+1073741824int*c[1]+1073741824int*c[2]+1073741824int*c[3]+1073741824int*c[4]+1073741824int*c[5]}
pub open spec fn even_difference_1_3_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+268435456int*c[1]+67108864int*c[2]+16777216int*c[3]+4194304int*c[4]+1048576int*c[5]}
pub open spec fn even_difference_1_3_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+20971520int*c[2]+22020096int*c[3]+22282240int*c[4]+22347776int*c[5]}
pub proof fn even_difference_1_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_1_3_before(c)==1int*even_difference_1_3_rhs(c)+48int*even_difference_1_3_after(c),
        even_difference_1_3_before(c)>=1int*even_difference_1_3_rhs(c),
        0<=even_difference_1_3_after(c)<=22347776int*mass(c),
        (even_difference_1_3_before(c)-1int*even_difference_1_3_rhs(c))%48int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_1_3_after(c),48int);
}
pub open spec fn even_difference_1_2_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+268435456int*c[1]+67108864int*c[2]+16777216int*c[3]+4194304int*c[4]+1048576int*c[5]}
pub open spec fn even_difference_1_2_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+67108864int*c[1]+4194304int*c[2]+262144int*c[3]+16384int*c[4]+1024int*c[5]}
pub open spec fn even_difference_1_2_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+5242880int*c[2]+1376256int*c[3]+348160int*c[4]+87296int*c[5]}
pub proof fn even_difference_1_2(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_1_2_before(c)==1int*even_difference_1_2_rhs(c)+12int*even_difference_1_2_after(c),
        even_difference_1_2_before(c)>=1int*even_difference_1_2_rhs(c),
        0<=even_difference_1_2_after(c)<=16777216int*mass(c),
        (even_difference_1_2_before(c)-1int*even_difference_1_2_rhs(c))%12int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_1_2_after(c),12int);
}
pub open spec fn even_difference_1_1_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+67108864int*c[1]+4194304int*c[2]+262144int*c[3]+16384int*c[4]+1024int*c[5]}
pub open spec fn even_difference_1_1_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_difference_1_1_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub proof fn even_difference_1_1(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_1_1_before(c)==1int*even_difference_1_1_rhs(c)+3int*even_difference_1_1_after(c),
        even_difference_1_1_before(c)>=1int*even_difference_1_1_rhs(c),
        0<=even_difference_1_1_after(c)<=16777216int*mass(c),
        (even_difference_1_1_before(c)-1int*even_difference_1_1_rhs(c))%3int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_1_1_after(c),3int);
}
pub open spec fn even_difference_2_5_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+335544320int*c[2]+5637144576int*c[3]+91268055040int*c[4]+1464583847936int*c[5]}
pub open spec fn even_difference_2_5_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+83886080int*c[2]+352321536int*c[3]+1426063360int*c[4]+5721030656int*c[5]}
pub open spec fn even_difference_2_5_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+5505024int*c[3]+93585408int*c[4]+1519648768int*c[5]}
pub proof fn even_difference_2_5(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_2_5_before(c)==1int*even_difference_2_5_rhs(c)+960int*even_difference_2_5_after(c),
        even_difference_2_5_before(c)>=1int*even_difference_2_5_rhs(c),
        0<=even_difference_2_5_after(c)<=1519648768int*mass(c),
        (even_difference_2_5_before(c)-1int*even_difference_2_5_rhs(c))%960int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_2_5_after(c),960int);
}
pub open spec fn even_difference_2_4_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+83886080int*c[2]+352321536int*c[3]+1426063360int*c[4]+5721030656int*c[5]}
pub open spec fn even_difference_2_4_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+20971520int*c[2]+22020096int*c[3]+22282240int*c[4]+22347776int*c[5]}
pub open spec fn even_difference_2_4_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+1376256int*c[3]+5849088int*c[4]+23744512int*c[5]}
pub proof fn even_difference_2_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_2_4_before(c)==1int*even_difference_2_4_rhs(c)+240int*even_difference_2_4_after(c),
        even_difference_2_4_before(c)>=1int*even_difference_2_4_rhs(c),
        0<=even_difference_2_4_after(c)<=23744512int*mass(c),
        (even_difference_2_4_before(c)-1int*even_difference_2_4_rhs(c))%240int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_2_4_after(c),240int);
}
pub open spec fn even_difference_2_3_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+20971520int*c[2]+22020096int*c[3]+22282240int*c[4]+22347776int*c[5]}
pub open spec fn even_difference_2_3_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+5242880int*c[2]+1376256int*c[3]+348160int*c[4]+87296int*c[5]}
pub open spec fn even_difference_2_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+344064int*c[3]+365568int*c[4]+371008int*c[5]}
pub proof fn even_difference_2_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_2_3_before(c)==1int*even_difference_2_3_rhs(c)+60int*even_difference_2_3_after(c),
        even_difference_2_3_before(c)>=1int*even_difference_2_3_rhs(c),
        0<=even_difference_2_3_after(c)<=371008int*mass(c),
        (even_difference_2_3_before(c)-1int*even_difference_2_3_rhs(c))%60int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_2_3_after(c),60int);
}
pub open spec fn even_difference_2_2_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+5242880int*c[2]+1376256int*c[3]+348160int*c[4]+87296int*c[5]}
pub open spec fn even_difference_2_2_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub open spec fn even_difference_2_2_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub proof fn even_difference_2_2(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_2_2_before(c)==1int*even_difference_2_2_rhs(c)+15int*even_difference_2_2_after(c),
        even_difference_2_2_before(c)>=1int*even_difference_2_2_rhs(c),
        0<=even_difference_2_2_after(c)<=262144int*mass(c),
        (even_difference_2_2_before(c)-1int*even_difference_2_2_rhs(c))%15int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_2_2_after(c),15int);
}
pub open spec fn even_difference_3_5_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+5505024int*c[3]+93585408int*c[4]+1519648768int*c[5]}
pub open spec fn even_difference_3_5_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+1376256int*c[3]+5849088int*c[4]+23744512int*c[5]}
pub open spec fn even_difference_3_5_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+87040int*c[4]+1484032int*c[5]}
pub proof fn even_difference_3_5(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_3_5_before(c)==1int*even_difference_3_5_rhs(c)+1008int*even_difference_3_5_after(c),
        even_difference_3_5_before(c)>=1int*even_difference_3_5_rhs(c),
        0<=even_difference_3_5_after(c)<=1484032int*mass(c),
        (even_difference_3_5_before(c)-1int*even_difference_3_5_rhs(c))%1008int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_3_5_after(c),1008int);
}
pub open spec fn even_difference_3_4_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+1376256int*c[3]+5849088int*c[4]+23744512int*c[5]}
pub open spec fn even_difference_3_4_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+344064int*c[3]+365568int*c[4]+371008int*c[5]}
pub open spec fn even_difference_3_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+21760int*c[4]+92752int*c[5]}
pub proof fn even_difference_3_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_3_4_before(c)==1int*even_difference_3_4_rhs(c)+252int*even_difference_3_4_after(c),
        even_difference_3_4_before(c)>=1int*even_difference_3_4_rhs(c),
        0<=even_difference_3_4_after(c)<=92752int*mass(c),
        (even_difference_3_4_before(c)-1int*even_difference_3_4_rhs(c))%252int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_3_4_after(c),252int);
}
pub open spec fn even_difference_3_3_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+344064int*c[3]+365568int*c[4]+371008int*c[5]}
pub open spec fn even_difference_3_3_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub open spec fn even_difference_3_3_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub proof fn even_difference_3_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_3_3_before(c)==1int*even_difference_3_3_rhs(c)+63int*even_difference_3_3_after(c),
        even_difference_3_3_before(c)>=1int*even_difference_3_3_rhs(c),
        0<=even_difference_3_3_after(c)<=5797int*mass(c),
        (even_difference_3_3_before(c)-1int*even_difference_3_3_rhs(c))%63int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_3_3_after(c),63int);
}
pub open spec fn even_difference_4_5_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+87040int*c[4]+1484032int*c[5]}
pub open spec fn even_difference_4_5_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+21760int*c[4]+92752int*c[5]}
pub open spec fn even_difference_4_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1364int*c[5]}
pub proof fn even_difference_4_5(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_4_5_before(c)==1int*even_difference_4_5_rhs(c)+1020int*even_difference_4_5_after(c),
        even_difference_4_5_before(c)>=1int*even_difference_4_5_rhs(c),
        0<=even_difference_4_5_after(c)<=1364int*mass(c),
        (even_difference_4_5_before(c)-1int*even_difference_4_5_rhs(c))%1020int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_4_5_after(c),1020int);
}
pub open spec fn even_difference_4_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+21760int*c[4]+92752int*c[5]}
pub open spec fn even_difference_4_4_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub open spec fn even_difference_4_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+341int*c[5]}
pub proof fn even_difference_4_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_4_4_before(c)==1int*even_difference_4_4_rhs(c)+255int*even_difference_4_4_after(c),
        even_difference_4_4_before(c)>=1int*even_difference_4_4_rhs(c),
        0<=even_difference_4_4_after(c)<=341int*mass(c),
        (even_difference_4_4_before(c)-1int*even_difference_4_4_rhs(c))%255int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_4_4_after(c),255int);
}
pub open spec fn even_difference_5_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1364int*c[5]}
pub open spec fn even_difference_5_5_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+341int*c[5]}
pub open spec fn even_difference_5_5_after(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub proof fn even_difference_5_5(c:Seq<int>)
    requires nonnegative(c),
    ensures even_difference_5_5_before(c)==1int*even_difference_5_5_rhs(c)+1023int*even_difference_5_5_after(c),
        even_difference_5_5_before(c)>=1int*even_difference_5_5_rhs(c),
        0<=even_difference_5_5_after(c)<=1int*mass(c),
        (even_difference_5_5_before(c)-1int*even_difference_5_5_rhs(c))%1023int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_difference_5_5_after(c),1023int);
}
pub open spec fn even_convert_4_4_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+341int*c[5]}
pub open spec fn even_convert_4_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub open spec fn even_convert_4_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+85int*c[5]}
pub proof fn even_convert_4_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_4_4_before(c)==256int*even_convert_4_4_rhs(c)+1int*even_convert_4_4_after(c),
        even_convert_4_4_before(c)>=256int*even_convert_4_4_rhs(c),
        0<=even_convert_4_4_after(c)<=85int*mass(c),
        (even_convert_4_4_before(c)-256int*even_convert_4_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_4_4_after(c),1int);
}
pub open spec fn even_convert_3_3_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub open spec fn even_convert_3_3_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+85int*c[5]}
pub open spec fn even_convert_3_3_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+1344int*c[4]+357int*c[5]}
pub proof fn even_convert_3_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_3_3_before(c)==64int*even_convert_3_3_rhs(c)+1int*even_convert_3_3_after(c),
        even_convert_3_3_before(c)>=64int*even_convert_3_3_rhs(c),
        0<=even_convert_3_3_after(c)<=4096int*mass(c),
        (even_convert_3_3_before(c)-64int*even_convert_3_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_3_3_after(c),1int);
}
pub open spec fn even_convert_3_4_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+85int*c[5]}
pub open spec fn even_convert_3_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub open spec fn even_convert_3_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+21int*c[5]}
pub proof fn even_convert_3_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_3_4_before(c)==64int*even_convert_3_4_rhs(c)+1int*even_convert_3_4_after(c),
        even_convert_3_4_before(c)>=64int*even_convert_3_4_rhs(c),
        0<=even_convert_3_4_after(c)<=64int*mass(c),
        (even_convert_3_4_before(c)-64int*even_convert_3_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_3_4_after(c),1int);
}
pub open spec fn even_convert_2_2_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub open spec fn even_convert_2_2_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+1344int*c[4]+357int*c[5]}
pub open spec fn even_convert_2_2_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+20480int*c[3]+1344int*c[4]+85int*c[5]}
pub proof fn even_convert_2_2(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_2_2_before(c)==16int*even_convert_2_2_rhs(c)+1int*even_convert_2_2_after(c),
        even_convert_2_2_before(c)>=16int*even_convert_2_2_rhs(c),
        0<=even_convert_2_2_after(c)<=262144int*mass(c),
        (even_convert_2_2_before(c)-16int*even_convert_2_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_2_2_after(c),1int);
}
pub open spec fn even_convert_2_3_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+1344int*c[4]+357int*c[5]}
pub open spec fn even_convert_2_3_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+21int*c[5]}
pub open spec fn even_convert_2_3_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+320int*c[4]+21int*c[5]}
pub proof fn even_convert_2_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_2_3_before(c)==16int*even_convert_2_3_rhs(c)+1int*even_convert_2_3_after(c),
        even_convert_2_3_before(c)>=16int*even_convert_2_3_rhs(c),
        0<=even_convert_2_3_after(c)<=4096int*mass(c),
        (even_convert_2_3_before(c)-16int*even_convert_2_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_2_3_after(c),1int);
}
pub open spec fn even_convert_2_4_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+21int*c[5]}
pub open spec fn even_convert_2_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub open spec fn even_convert_2_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+5int*c[5]}
pub proof fn even_convert_2_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_2_4_before(c)==16int*even_convert_2_4_rhs(c)+1int*even_convert_2_4_after(c),
        even_convert_2_4_before(c)>=16int*even_convert_2_4_rhs(c),
        0<=even_convert_2_4_after(c)<=64int*mass(c),
        (even_convert_2_4_before(c)-16int*even_convert_2_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_2_4_after(c),1int);
}
pub open spec fn even_convert_1_1_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub open spec fn even_convert_1_1_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+20480int*c[3]+1344int*c[4]+85int*c[5]}
pub open spec fn even_convert_1_1_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub proof fn even_convert_1_1(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_1_1_before(c)==4int*even_convert_1_1_rhs(c)+1int*even_convert_1_1_after(c),
        even_convert_1_1_before(c)>=4int*even_convert_1_1_rhs(c),
        0<=even_convert_1_1_after(c)<=16777216int*mass(c),
        (even_convert_1_1_before(c)-4int*even_convert_1_1_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_1_1_after(c),1int);
}
pub open spec fn even_convert_1_2_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+20480int*c[3]+1344int*c[4]+85int*c[5]}
pub open spec fn even_convert_1_2_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+320int*c[4]+21int*c[5]}
pub open spec fn even_convert_1_2_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub proof fn even_convert_1_2(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_1_2_before(c)==4int*even_convert_1_2_rhs(c)+1int*even_convert_1_2_after(c),
        even_convert_1_2_before(c)>=4int*even_convert_1_2_rhs(c),
        0<=even_convert_1_2_after(c)<=262144int*mass(c),
        (even_convert_1_2_before(c)-4int*even_convert_1_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_1_2_after(c),1int);
}
pub open spec fn even_convert_1_3_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+320int*c[4]+21int*c[5]}
pub open spec fn even_convert_1_3_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+5int*c[5]}
pub open spec fn even_convert_1_3_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+64int*c[4]+1int*c[5]}
pub proof fn even_convert_1_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_1_3_before(c)==4int*even_convert_1_3_rhs(c)+1int*even_convert_1_3_after(c),
        even_convert_1_3_before(c)>=4int*even_convert_1_3_rhs(c),
        0<=even_convert_1_3_after(c)<=4096int*mass(c),
        (even_convert_1_3_before(c)-4int*even_convert_1_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_1_3_after(c),1int);
}
pub open spec fn even_convert_1_4_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+5int*c[5]}
pub open spec fn even_convert_1_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub open spec fn even_convert_1_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1int*c[5]}
pub proof fn even_convert_1_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_1_4_before(c)==4int*even_convert_1_4_rhs(c)+1int*even_convert_1_4_after(c),
        even_convert_1_4_before(c)>=4int*even_convert_1_4_rhs(c),
        0<=even_convert_1_4_after(c)<=64int*mass(c),
        (even_convert_1_4_before(c)-4int*even_convert_1_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_1_4_after(c),1int);
}
pub open spec fn even_convert_0_0_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_0_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_0_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]}
pub proof fn even_convert_0_0(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_0_0_before(c)==1int*even_convert_0_0_rhs(c)+1int*even_convert_0_0_after(c),
        even_convert_0_0_before(c)>=1int*even_convert_0_0_rhs(c),
        0<=even_convert_0_0_after(c)<=1073741824int*mass(c),
        (even_convert_0_0_before(c)-1int*even_convert_0_0_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_0_0_after(c),1int);
}
pub open spec fn even_convert_0_1_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_1_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_1_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]}
pub proof fn even_convert_0_1(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_0_1_before(c)==1int*even_convert_0_1_rhs(c)+1int*even_convert_0_1_after(c),
        even_convert_0_1_before(c)>=1int*even_convert_0_1_rhs(c),
        0<=even_convert_0_1_after(c)<=16777216int*mass(c),
        (even_convert_0_1_before(c)-1int*even_convert_0_1_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_0_1_after(c),1int);
}
pub open spec fn even_convert_0_2_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_2_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_2_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]}
pub proof fn even_convert_0_2(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_0_2_before(c)==1int*even_convert_0_2_rhs(c)+1int*even_convert_0_2_after(c),
        even_convert_0_2_before(c)>=1int*even_convert_0_2_rhs(c),
        0<=even_convert_0_2_after(c)<=262144int*mass(c),
        (even_convert_0_2_before(c)-1int*even_convert_0_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_0_2_after(c),1int);
}
pub open spec fn even_convert_0_3_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_3_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_3_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]}
pub proof fn even_convert_0_3(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_0_3_before(c)==1int*even_convert_0_3_rhs(c)+1int*even_convert_0_3_after(c),
        even_convert_0_3_before(c)>=1int*even_convert_0_3_rhs(c),
        0<=even_convert_0_3_after(c)<=4096int*mass(c),
        (even_convert_0_3_before(c)-1int*even_convert_0_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_0_3_after(c),1int);
}
pub open spec fn even_convert_0_4_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1int*c[5]}
pub open spec fn even_convert_0_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub open spec fn even_convert_0_4_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]}
pub proof fn even_convert_0_4(c:Seq<int>)
    requires nonnegative(c),
    ensures even_convert_0_4_before(c)==1int*even_convert_0_4_rhs(c)+1int*even_convert_0_4_after(c),
        even_convert_0_4_before(c)>=1int*even_convert_0_4_rhs(c),
        0<=even_convert_0_4_after(c)<=64int*mass(c),
        (even_convert_0_4_before(c)-1int*even_convert_0_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(even_convert_0_4_after(c),1int);
}
pub open spec fn odd_difference_1_6_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+4398046511104int*c[1]+281474976710656int*c[2]+18014398509481984int*c[3]+1152921504606846976int*c[4]+73786976294838206464int*c[5]+4722366482869645213696int*c[6]}
pub open spec fn odd_difference_1_6_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1099511627776int*c[1]+17592186044416int*c[2]+281474976710656int*c[3]+4503599627370496int*c[4]+72057594037927936int*c[5]+1152921504606846976int*c[6]}
pub open spec fn odd_difference_1_6_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+85899345920int*c[2]+5772436045824int*c[3]+373833953443840int*c[4]+23995741764583424int*c[5]+1536853372840181760int*c[6]}
pub proof fn odd_difference_1_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_6_before(c)==1int*odd_difference_1_6_rhs(c)+3072int*odd_difference_1_6_after(c),
        odd_difference_1_6_before(c)>=1int*odd_difference_1_6_rhs(c),
        0<=odd_difference_1_6_after(c)<=1536853372840181760int*mass(c),
        (odd_difference_1_6_before(c)-1int*odd_difference_1_6_rhs(c))%3072int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_6_after(c),3072int);
}
pub open spec fn odd_difference_1_5_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1099511627776int*c[1]+17592186044416int*c[2]+281474976710656int*c[3]+4503599627370496int*c[4]+72057594037927936int*c[5]+1152921504606846976int*c[6]}
pub open spec fn odd_difference_1_5_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+274877906944int*c[1]+1099511627776int*c[2]+4398046511104int*c[3]+17592186044416int*c[4]+70368744177664int*c[5]+281474976710656int*c[6]}
pub open spec fn odd_difference_1_5_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+21474836480int*c[2]+360777252864int*c[3]+5841155522560int*c[4]+93733366267904int*c[5]+1500833371914240int*c[6]}
pub proof fn odd_difference_1_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_5_before(c)==1int*odd_difference_1_5_rhs(c)+768int*odd_difference_1_5_after(c),
        odd_difference_1_5_before(c)>=1int*odd_difference_1_5_rhs(c),
        0<=odd_difference_1_5_after(c)<=1500833371914240int*mass(c),
        (odd_difference_1_5_before(c)-1int*odd_difference_1_5_rhs(c))%768int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_5_after(c),768int);
}
pub open spec fn odd_difference_1_4_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+274877906944int*c[1]+1099511627776int*c[2]+4398046511104int*c[3]+17592186044416int*c[4]+70368744177664int*c[5]+281474976710656int*c[6]}
pub open spec fn odd_difference_1_4_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+68719476736int*c[1]+68719476736int*c[2]+68719476736int*c[3]+68719476736int*c[4]+68719476736int*c[5]+68719476736int*c[6]}
pub open spec fn odd_difference_1_4_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+5368709120int*c[2]+22548578304int*c[3]+91268055040int*c[4]+366145961984int*c[5]+1465657589760int*c[6]}
pub proof fn odd_difference_1_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_4_before(c)==1int*odd_difference_1_4_rhs(c)+192int*odd_difference_1_4_after(c),
        odd_difference_1_4_before(c)>=1int*odd_difference_1_4_rhs(c),
        0<=odd_difference_1_4_after(c)<=1465657589760int*mass(c),
        (odd_difference_1_4_before(c)-1int*odd_difference_1_4_rhs(c))%192int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_4_after(c),192int);
}
pub open spec fn odd_difference_1_3_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+68719476736int*c[1]+68719476736int*c[2]+68719476736int*c[3]+68719476736int*c[4]+68719476736int*c[5]+68719476736int*c[6]}
pub open spec fn odd_difference_1_3_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+17179869184int*c[1]+4294967296int*c[2]+1073741824int*c[3]+268435456int*c[4]+67108864int*c[5]+16777216int*c[6]}
pub open spec fn odd_difference_1_3_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+1342177280int*c[2]+1409286144int*c[3]+1426063360int*c[4]+1430257664int*c[5]+1431306240int*c[6]}
pub proof fn odd_difference_1_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_3_before(c)==1int*odd_difference_1_3_rhs(c)+48int*odd_difference_1_3_after(c),
        odd_difference_1_3_before(c)>=1int*odd_difference_1_3_rhs(c),
        0<=odd_difference_1_3_after(c)<=1431306240int*mass(c),
        (odd_difference_1_3_before(c)-1int*odd_difference_1_3_rhs(c))%48int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_3_after(c),48int);
}
pub open spec fn odd_difference_1_2_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+17179869184int*c[1]+4294967296int*c[2]+1073741824int*c[3]+268435456int*c[4]+67108864int*c[5]+16777216int*c[6]}
pub open spec fn odd_difference_1_2_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+4294967296int*c[1]+268435456int*c[2]+16777216int*c[3]+1048576int*c[4]+65536int*c[5]+4096int*c[6]}
pub open spec fn odd_difference_1_2_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+335544320int*c[2]+88080384int*c[3]+22282240int*c[4]+5586944int*c[5]+1397760int*c[6]}
pub proof fn odd_difference_1_2(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_2_before(c)==1int*odd_difference_1_2_rhs(c)+12int*odd_difference_1_2_after(c),
        odd_difference_1_2_before(c)>=1int*odd_difference_1_2_rhs(c),
        0<=odd_difference_1_2_after(c)<=1073741824int*mass(c),
        (odd_difference_1_2_before(c)-1int*odd_difference_1_2_rhs(c))%12int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_2_after(c),12int);
}
pub open spec fn odd_difference_1_1_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+4294967296int*c[1]+268435456int*c[2]+16777216int*c[3]+1048576int*c[4]+65536int*c[5]+4096int*c[6]}
pub open spec fn odd_difference_1_1_rhs(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_difference_1_1_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub proof fn odd_difference_1_1(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_1_1_before(c)==1int*odd_difference_1_1_rhs(c)+3int*odd_difference_1_1_after(c),
        odd_difference_1_1_before(c)>=1int*odd_difference_1_1_rhs(c),
        0<=odd_difference_1_1_after(c)<=1073741824int*mass(c),
        (odd_difference_1_1_before(c)-1int*odd_difference_1_1_rhs(c))%3int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_1_1_after(c),3int);
}
pub open spec fn odd_difference_2_6_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+85899345920int*c[2]+5772436045824int*c[3]+373833953443840int*c[4]+23995741764583424int*c[5]+1536853372840181760int*c[6]}
pub open spec fn odd_difference_2_6_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+21474836480int*c[2]+360777252864int*c[3]+5841155522560int*c[4]+93733366267904int*c[5]+1500833371914240int*c[6]}
pub open spec fn odd_difference_2_6_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1409286144int*c[3]+95831457792int*c[4]+6224481353728int*c[5]+399831390486528int*c[6]}
pub proof fn odd_difference_2_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_2_6_before(c)==1int*odd_difference_2_6_rhs(c)+3840int*odd_difference_2_6_after(c),
        odd_difference_2_6_before(c)>=1int*odd_difference_2_6_rhs(c),
        0<=odd_difference_2_6_after(c)<=399831390486528int*mass(c),
        (odd_difference_2_6_before(c)-1int*odd_difference_2_6_rhs(c))%3840int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_2_6_after(c),3840int);
}
pub open spec fn odd_difference_2_5_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+21474836480int*c[2]+360777252864int*c[3]+5841155522560int*c[4]+93733366267904int*c[5]+1500833371914240int*c[6]}
pub open spec fn odd_difference_2_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+5368709120int*c[2]+22548578304int*c[3]+91268055040int*c[4]+366145961984int*c[5]+1465657589760int*c[6]}
pub open spec fn odd_difference_2_5_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+352321536int*c[3]+5989466112int*c[4]+97257521152int*c[5]+1561841369088int*c[6]}
pub proof fn odd_difference_2_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_2_5_before(c)==1int*odd_difference_2_5_rhs(c)+960int*odd_difference_2_5_after(c),
        odd_difference_2_5_before(c)>=1int*odd_difference_2_5_rhs(c),
        0<=odd_difference_2_5_after(c)<=1561841369088int*mass(c),
        (odd_difference_2_5_before(c)-1int*odd_difference_2_5_rhs(c))%960int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_2_5_after(c),960int);
}
pub open spec fn odd_difference_2_4_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+5368709120int*c[2]+22548578304int*c[3]+91268055040int*c[4]+366145961984int*c[5]+1465657589760int*c[6]}
pub open spec fn odd_difference_2_4_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+1342177280int*c[2]+1409286144int*c[3]+1426063360int*c[4]+1430257664int*c[5]+1431306240int*c[6]}
pub open spec fn odd_difference_2_4_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+88080384int*c[3]+374341632int*c[4]+1519648768int*c[5]+6100942848int*c[6]}
pub proof fn odd_difference_2_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_2_4_before(c)==1int*odd_difference_2_4_rhs(c)+240int*odd_difference_2_4_after(c),
        odd_difference_2_4_before(c)>=1int*odd_difference_2_4_rhs(c),
        0<=odd_difference_2_4_after(c)<=6100942848int*mass(c),
        (odd_difference_2_4_before(c)-1int*odd_difference_2_4_rhs(c))%240int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_2_4_after(c),240int);
}
pub open spec fn odd_difference_2_3_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+1342177280int*c[2]+1409286144int*c[3]+1426063360int*c[4]+1430257664int*c[5]+1431306240int*c[6]}
pub open spec fn odd_difference_2_3_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+335544320int*c[2]+88080384int*c[3]+22282240int*c[4]+5586944int*c[5]+1397760int*c[6]}
pub open spec fn odd_difference_2_3_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+22020096int*c[3]+23396352int*c[4]+23744512int*c[5]+23831808int*c[6]}
pub proof fn odd_difference_2_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_2_3_before(c)==1int*odd_difference_2_3_rhs(c)+60int*odd_difference_2_3_after(c),
        odd_difference_2_3_before(c)>=1int*odd_difference_2_3_rhs(c),
        0<=odd_difference_2_3_after(c)<=23831808int*mass(c),
        (odd_difference_2_3_before(c)-1int*odd_difference_2_3_rhs(c))%60int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_2_3_after(c),60int);
}
pub open spec fn odd_difference_2_2_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+335544320int*c[2]+88080384int*c[3]+22282240int*c[4]+5586944int*c[5]+1397760int*c[6]}
pub open spec fn odd_difference_2_2_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub open spec fn odd_difference_2_2_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub proof fn odd_difference_2_2(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_2_2_before(c)==1int*odd_difference_2_2_rhs(c)+15int*odd_difference_2_2_after(c),
        odd_difference_2_2_before(c)>=1int*odd_difference_2_2_rhs(c),
        0<=odd_difference_2_2_after(c)<=16777216int*mass(c),
        (odd_difference_2_2_before(c)-1int*odd_difference_2_2_rhs(c))%15int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_2_2_after(c),15int);
}
pub open spec fn odd_difference_3_6_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1409286144int*c[3]+95831457792int*c[4]+6224481353728int*c[5]+399831390486528int*c[6]}
pub open spec fn odd_difference_3_6_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+352321536int*c[3]+5989466112int*c[4]+97257521152int*c[5]+1561841369088int*c[6]}
pub open spec fn odd_difference_3_6_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+22282240int*c[4]+1519648768int*c[5]+98777169920int*c[6]}
pub proof fn odd_difference_3_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_3_6_before(c)==1int*odd_difference_3_6_rhs(c)+4032int*odd_difference_3_6_after(c),
        odd_difference_3_6_before(c)>=1int*odd_difference_3_6_rhs(c),
        0<=odd_difference_3_6_after(c)<=98777169920int*mass(c),
        (odd_difference_3_6_before(c)-1int*odd_difference_3_6_rhs(c))%4032int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_3_6_after(c),4032int);
}
pub open spec fn odd_difference_3_5_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+352321536int*c[3]+5989466112int*c[4]+97257521152int*c[5]+1561841369088int*c[6]}
pub open spec fn odd_difference_3_5_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+88080384int*c[3]+374341632int*c[4]+1519648768int*c[5]+6100942848int*c[6]}
pub open spec fn odd_difference_3_5_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+5570560int*c[4]+94978048int*c[5]+1543393280int*c[6]}
pub proof fn odd_difference_3_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_3_5_before(c)==1int*odd_difference_3_5_rhs(c)+1008int*odd_difference_3_5_after(c),
        odd_difference_3_5_before(c)>=1int*odd_difference_3_5_rhs(c),
        0<=odd_difference_3_5_after(c)<=1543393280int*mass(c),
        (odd_difference_3_5_before(c)-1int*odd_difference_3_5_rhs(c))%1008int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_3_5_after(c),1008int);
}
pub open spec fn odd_difference_3_4_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+88080384int*c[3]+374341632int*c[4]+1519648768int*c[5]+6100942848int*c[6]}
pub open spec fn odd_difference_3_4_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+22020096int*c[3]+23396352int*c[4]+23744512int*c[5]+23831808int*c[6]}
pub open spec fn odd_difference_3_4_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+1392640int*c[4]+5936128int*c[5]+24115520int*c[6]}
pub proof fn odd_difference_3_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_3_4_before(c)==1int*odd_difference_3_4_rhs(c)+252int*odd_difference_3_4_after(c),
        odd_difference_3_4_before(c)>=1int*odd_difference_3_4_rhs(c),
        0<=odd_difference_3_4_after(c)<=24115520int*mass(c),
        (odd_difference_3_4_before(c)-1int*odd_difference_3_4_rhs(c))%252int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_3_4_after(c),252int);
}
pub open spec fn odd_difference_3_3_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+22020096int*c[3]+23396352int*c[4]+23744512int*c[5]+23831808int*c[6]}
pub open spec fn odd_difference_3_3_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub open spec fn odd_difference_3_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub proof fn odd_difference_3_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_3_3_before(c)==1int*odd_difference_3_3_rhs(c)+63int*odd_difference_3_3_after(c),
        odd_difference_3_3_before(c)>=1int*odd_difference_3_3_rhs(c),
        0<=odd_difference_3_3_after(c)<=376805int*mass(c),
        (odd_difference_3_3_before(c)-1int*odd_difference_3_3_rhs(c))%63int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_3_3_after(c),63int);
}
pub open spec fn odd_difference_4_6_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+22282240int*c[4]+1519648768int*c[5]+98777169920int*c[6]}
pub open spec fn odd_difference_4_6_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+5570560int*c[4]+94978048int*c[5]+1543393280int*c[6]}
pub open spec fn odd_difference_4_6_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+349184int*c[5]+23831808int*c[6]}
pub proof fn odd_difference_4_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_4_6_before(c)==1int*odd_difference_4_6_rhs(c)+4080int*odd_difference_4_6_after(c),
        odd_difference_4_6_before(c)>=1int*odd_difference_4_6_rhs(c),
        0<=odd_difference_4_6_after(c)<=23831808int*mass(c),
        (odd_difference_4_6_before(c)-1int*odd_difference_4_6_rhs(c))%4080int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_4_6_after(c),4080int);
}
pub open spec fn odd_difference_4_5_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+5570560int*c[4]+94978048int*c[5]+1543393280int*c[6]}
pub open spec fn odd_difference_4_5_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+1392640int*c[4]+5936128int*c[5]+24115520int*c[6]}
pub open spec fn odd_difference_4_5_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+87296int*c[5]+1489488int*c[6]}
pub proof fn odd_difference_4_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_4_5_before(c)==1int*odd_difference_4_5_rhs(c)+1020int*odd_difference_4_5_after(c),
        odd_difference_4_5_before(c)>=1int*odd_difference_4_5_rhs(c),
        0<=odd_difference_4_5_after(c)<=1489488int*mass(c),
        (odd_difference_4_5_before(c)-1int*odd_difference_4_5_rhs(c))%1020int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_4_5_after(c),1020int);
}
pub open spec fn odd_difference_4_4_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+1392640int*c[4]+5936128int*c[5]+24115520int*c[6]}
pub open spec fn odd_difference_4_4_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub open spec fn odd_difference_4_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub proof fn odd_difference_4_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_4_4_before(c)==1int*odd_difference_4_4_rhs(c)+255int*odd_difference_4_4_after(c),
        odd_difference_4_4_before(c)>=1int*odd_difference_4_4_rhs(c),
        0<=odd_difference_4_4_after(c)<=93093int*mass(c),
        (odd_difference_4_4_before(c)-1int*odd_difference_4_4_rhs(c))%255int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_4_4_after(c),255int);
}
pub open spec fn odd_difference_5_6_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+349184int*c[5]+23831808int*c[6]}
pub open spec fn odd_difference_5_6_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+87296int*c[5]+1489488int*c[6]}
pub open spec fn odd_difference_5_6_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5460int*c[6]}
pub proof fn odd_difference_5_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_5_6_before(c)==1int*odd_difference_5_6_rhs(c)+4092int*odd_difference_5_6_after(c),
        odd_difference_5_6_before(c)>=1int*odd_difference_5_6_rhs(c),
        0<=odd_difference_5_6_after(c)<=5460int*mass(c),
        (odd_difference_5_6_before(c)-1int*odd_difference_5_6_rhs(c))%4092int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_5_6_after(c),4092int);
}
pub open spec fn odd_difference_5_5_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+87296int*c[5]+1489488int*c[6]}
pub open spec fn odd_difference_5_5_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub open spec fn odd_difference_5_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1365int*c[6]}
pub proof fn odd_difference_5_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_5_5_before(c)==1int*odd_difference_5_5_rhs(c)+1023int*odd_difference_5_5_after(c),
        odd_difference_5_5_before(c)>=1int*odd_difference_5_5_rhs(c),
        0<=odd_difference_5_5_after(c)<=1365int*mass(c),
        (odd_difference_5_5_before(c)-1int*odd_difference_5_5_rhs(c))%1023int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_5_5_after(c),1023int);
}
pub open spec fn odd_difference_6_6_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5460int*c[6]}
pub open spec fn odd_difference_6_6_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1365int*c[6]}
pub open spec fn odd_difference_6_6_after(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub proof fn odd_difference_6_6(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_difference_6_6_before(c)==1int*odd_difference_6_6_rhs(c)+4095int*odd_difference_6_6_after(c),
        odd_difference_6_6_before(c)>=1int*odd_difference_6_6_rhs(c),
        0<=odd_difference_6_6_after(c)<=1int*mass(c),
        (odd_difference_6_6_before(c)-1int*odd_difference_6_6_rhs(c))%4095int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_difference_6_6_after(c),4095int);
}
pub open spec fn odd_convert_5_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1365int*c[6]}
pub open spec fn odd_convert_5_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_5_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+341int*c[6]}
pub proof fn odd_convert_5_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_5_5_before(c)==1024int*odd_convert_5_5_rhs(c)+1int*odd_convert_5_5_after(c),
        odd_convert_5_5_before(c)>=1024int*odd_convert_5_5_rhs(c),
        0<=odd_convert_5_5_after(c)<=341int*mass(c),
        (odd_convert_5_5_before(c)-1024int*odd_convert_5_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_5_5_after(c),1int);
}
pub open spec fn odd_convert_4_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub open spec fn odd_convert_4_4_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+341int*c[6]}
pub open spec fn odd_convert_4_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+5440int*c[5]+5797int*c[6]}
pub proof fn odd_convert_4_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_4_4_before(c)==256int*odd_convert_4_4_rhs(c)+1int*odd_convert_4_4_after(c),
        odd_convert_4_4_before(c)>=256int*odd_convert_4_4_rhs(c),
        0<=odd_convert_4_4_after(c)<=5797int*mass(c),
        (odd_convert_4_4_before(c)-256int*odd_convert_4_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_4_4_after(c),1int);
}
pub open spec fn odd_convert_4_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+341int*c[6]}
pub open spec fn odd_convert_4_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_4_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+85int*c[6]}
pub proof fn odd_convert_4_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_4_5_before(c)==256int*odd_convert_4_5_rhs(c)+1int*odd_convert_4_5_after(c),
        odd_convert_4_5_before(c)>=256int*odd_convert_4_5_rhs(c),
        0<=odd_convert_4_5_after(c)<=85int*mass(c),
        (odd_convert_4_5_before(c)-256int*odd_convert_4_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_4_5_after(c),1int);
}
pub open spec fn odd_convert_3_3_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub open spec fn odd_convert_3_3_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+5440int*c[5]+5797int*c[6]}
pub open spec fn odd_convert_3_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+86016int*c[4]+22848int*c[5]+5797int*c[6]}
pub proof fn odd_convert_3_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_3_3_before(c)==64int*odd_convert_3_3_rhs(c)+1int*odd_convert_3_3_after(c),
        odd_convert_3_3_before(c)>=64int*odd_convert_3_3_rhs(c),
        0<=odd_convert_3_3_after(c)<=262144int*mass(c),
        (odd_convert_3_3_before(c)-64int*odd_convert_3_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_3_3_after(c),1int);
}
pub open spec fn odd_convert_3_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+5440int*c[5]+5797int*c[6]}
pub open spec fn odd_convert_3_4_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+85int*c[6]}
pub open spec fn odd_convert_3_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+1344int*c[5]+357int*c[6]}
pub proof fn odd_convert_3_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_3_4_before(c)==64int*odd_convert_3_4_rhs(c)+1int*odd_convert_3_4_after(c),
        odd_convert_3_4_before(c)>=64int*odd_convert_3_4_rhs(c),
        0<=odd_convert_3_4_after(c)<=4096int*mass(c),
        (odd_convert_3_4_before(c)-64int*odd_convert_3_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_3_4_after(c),1int);
}
pub open spec fn odd_convert_3_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+85int*c[6]}
pub open spec fn odd_convert_3_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_3_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+21int*c[6]}
pub proof fn odd_convert_3_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_3_5_before(c)==64int*odd_convert_3_5_rhs(c)+1int*odd_convert_3_5_after(c),
        odd_convert_3_5_before(c)>=64int*odd_convert_3_5_rhs(c),
        0<=odd_convert_3_5_after(c)<=64int*mass(c),
        (odd_convert_3_5_before(c)-64int*odd_convert_3_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_3_5_after(c),1int);
}
pub open spec fn odd_convert_2_2_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub open spec fn odd_convert_2_2_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+86016int*c[4]+22848int*c[5]+5797int*c[6]}
pub open spec fn odd_convert_2_2_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1310720int*c[3]+86016int*c[4]+5440int*c[5]+341int*c[6]}
pub proof fn odd_convert_2_2(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_2_2_before(c)==16int*odd_convert_2_2_rhs(c)+1int*odd_convert_2_2_after(c),
        odd_convert_2_2_before(c)>=16int*odd_convert_2_2_rhs(c),
        0<=odd_convert_2_2_after(c)<=16777216int*mass(c),
        (odd_convert_2_2_before(c)-16int*odd_convert_2_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_2_2_after(c),1int);
}
pub open spec fn odd_convert_2_3_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+86016int*c[4]+22848int*c[5]+5797int*c[6]}
pub open spec fn odd_convert_2_3_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+1344int*c[5]+357int*c[6]}
pub open spec fn odd_convert_2_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+20480int*c[4]+1344int*c[5]+85int*c[6]}
pub proof fn odd_convert_2_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_2_3_before(c)==16int*odd_convert_2_3_rhs(c)+1int*odd_convert_2_3_after(c),
        odd_convert_2_3_before(c)>=16int*odd_convert_2_3_rhs(c),
        0<=odd_convert_2_3_after(c)<=262144int*mass(c),
        (odd_convert_2_3_before(c)-16int*odd_convert_2_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_2_3_after(c),1int);
}
pub open spec fn odd_convert_2_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+1344int*c[5]+357int*c[6]}
pub open spec fn odd_convert_2_4_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+21int*c[6]}
pub open spec fn odd_convert_2_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+320int*c[5]+21int*c[6]}
pub proof fn odd_convert_2_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_2_4_before(c)==16int*odd_convert_2_4_rhs(c)+1int*odd_convert_2_4_after(c),
        odd_convert_2_4_before(c)>=16int*odd_convert_2_4_rhs(c),
        0<=odd_convert_2_4_after(c)<=4096int*mass(c),
        (odd_convert_2_4_before(c)-16int*odd_convert_2_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_2_4_after(c),1int);
}
pub open spec fn odd_convert_2_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+21int*c[6]}
pub open spec fn odd_convert_2_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_2_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5int*c[6]}
pub proof fn odd_convert_2_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_2_5_before(c)==16int*odd_convert_2_5_rhs(c)+1int*odd_convert_2_5_after(c),
        odd_convert_2_5_before(c)>=16int*odd_convert_2_5_rhs(c),
        0<=odd_convert_2_5_after(c)<=64int*mass(c),
        (odd_convert_2_5_before(c)-16int*odd_convert_2_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_2_5_after(c),1int);
}
pub open spec fn odd_convert_1_1_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub open spec fn odd_convert_1_1_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1310720int*c[3]+86016int*c[4]+5440int*c[5]+341int*c[6]}
pub open spec fn odd_convert_1_1_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub proof fn odd_convert_1_1(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_1_1_before(c)==4int*odd_convert_1_1_rhs(c)+1int*odd_convert_1_1_after(c),
        odd_convert_1_1_before(c)>=4int*odd_convert_1_1_rhs(c),
        0<=odd_convert_1_1_after(c)<=1073741824int*mass(c),
        (odd_convert_1_1_before(c)-4int*odd_convert_1_1_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_1_1_after(c),1int);
}
pub open spec fn odd_convert_1_2_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1310720int*c[3]+86016int*c[4]+5440int*c[5]+341int*c[6]}
pub open spec fn odd_convert_1_2_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+20480int*c[4]+1344int*c[5]+85int*c[6]}
pub open spec fn odd_convert_1_2_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub proof fn odd_convert_1_2(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_1_2_before(c)==4int*odd_convert_1_2_rhs(c)+1int*odd_convert_1_2_after(c),
        odd_convert_1_2_before(c)>=4int*odd_convert_1_2_rhs(c),
        0<=odd_convert_1_2_after(c)<=16777216int*mass(c),
        (odd_convert_1_2_before(c)-4int*odd_convert_1_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_1_2_after(c),1int);
}
pub open spec fn odd_convert_1_3_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+20480int*c[4]+1344int*c[5]+85int*c[6]}
pub open spec fn odd_convert_1_3_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+320int*c[5]+21int*c[6]}
pub open spec fn odd_convert_1_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub proof fn odd_convert_1_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_1_3_before(c)==4int*odd_convert_1_3_rhs(c)+1int*odd_convert_1_3_after(c),
        odd_convert_1_3_before(c)>=4int*odd_convert_1_3_rhs(c),
        0<=odd_convert_1_3_after(c)<=262144int*mass(c),
        (odd_convert_1_3_before(c)-4int*odd_convert_1_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_1_3_after(c),1int);
}
pub open spec fn odd_convert_1_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+320int*c[5]+21int*c[6]}
pub open spec fn odd_convert_1_4_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5int*c[6]}
pub open spec fn odd_convert_1_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+64int*c[5]+1int*c[6]}
pub proof fn odd_convert_1_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_1_4_before(c)==4int*odd_convert_1_4_rhs(c)+1int*odd_convert_1_4_after(c),
        odd_convert_1_4_before(c)>=4int*odd_convert_1_4_rhs(c),
        0<=odd_convert_1_4_after(c)<=4096int*mass(c),
        (odd_convert_1_4_before(c)-4int*odd_convert_1_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_1_4_after(c),1int);
}
pub open spec fn odd_convert_1_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5int*c[6]}
pub open spec fn odd_convert_1_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_1_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1int*c[6]}
pub proof fn odd_convert_1_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_1_5_before(c)==4int*odd_convert_1_5_rhs(c)+1int*odd_convert_1_5_after(c),
        odd_convert_1_5_before(c)>=4int*odd_convert_1_5_rhs(c),
        0<=odd_convert_1_5_after(c)<=64int*mass(c),
        (odd_convert_1_5_before(c)-4int*odd_convert_1_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_1_5_after(c),1int);
}
pub open spec fn odd_convert_0_0_before(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_0_rhs(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_0_after(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]}
pub proof fn odd_convert_0_0(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_0_before(c)==1int*odd_convert_0_0_rhs(c)+1int*odd_convert_0_0_after(c),
        odd_convert_0_0_before(c)>=1int*odd_convert_0_0_rhs(c),
        0<=odd_convert_0_0_after(c)<=68719476736int*mass(c),
        (odd_convert_0_0_before(c)-1int*odd_convert_0_0_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_0_after(c),1int);
}
pub open spec fn odd_convert_0_1_before(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_1_rhs(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_1_after(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]}
pub proof fn odd_convert_0_1(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_1_before(c)==1int*odd_convert_0_1_rhs(c)+1int*odd_convert_0_1_after(c),
        odd_convert_0_1_before(c)>=1int*odd_convert_0_1_rhs(c),
        0<=odd_convert_0_1_after(c)<=1073741824int*mass(c),
        (odd_convert_0_1_before(c)-1int*odd_convert_0_1_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_1_after(c),1int);
}
pub open spec fn odd_convert_0_2_before(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_2_rhs(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_2_after(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]}
pub proof fn odd_convert_0_2(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_2_before(c)==1int*odd_convert_0_2_rhs(c)+1int*odd_convert_0_2_after(c),
        odd_convert_0_2_before(c)>=1int*odd_convert_0_2_rhs(c),
        0<=odd_convert_0_2_after(c)<=16777216int*mass(c),
        (odd_convert_0_2_before(c)-1int*odd_convert_0_2_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_2_after(c),1int);
}
pub open spec fn odd_convert_0_3_before(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_3_rhs(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_3_after(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]}
pub proof fn odd_convert_0_3(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_3_before(c)==1int*odd_convert_0_3_rhs(c)+1int*odd_convert_0_3_after(c),
        odd_convert_0_3_before(c)>=1int*odd_convert_0_3_rhs(c),
        0<=odd_convert_0_3_after(c)<=262144int*mass(c),
        (odd_convert_0_3_before(c)-1int*odd_convert_0_3_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_3_after(c),1int);
}
pub open spec fn odd_convert_0_4_before(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_4_rhs(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_4_after(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]}
pub proof fn odd_convert_0_4(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_4_before(c)==1int*odd_convert_0_4_rhs(c)+1int*odd_convert_0_4_after(c),
        odd_convert_0_4_before(c)>=1int*odd_convert_0_4_rhs(c),
        0<=odd_convert_0_4_after(c)<=4096int*mass(c),
        (odd_convert_0_4_before(c)-1int*odd_convert_0_4_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_4_after(c),1int);
}
pub open spec fn odd_convert_0_5_before(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1int*c[6]}
pub open spec fn odd_convert_0_5_rhs(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub open spec fn odd_convert_0_5_after(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]}
pub proof fn odd_convert_0_5(c:Seq<int>)
    requires nonnegative(c),
    ensures odd_convert_0_5_before(c)==1int*odd_convert_0_5_rhs(c)+1int*odd_convert_0_5_after(c),
        odd_convert_0_5_before(c)>=1int*odd_convert_0_5_rhs(c),
        0<=odd_convert_0_5_after(c)<=64int*mass(c),
        (odd_convert_0_5_before(c)-1int*odd_convert_0_5_rhs(c))%1int==0,
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0);
    lemma_mod_multiples_basic(odd_convert_0_5_after(c),1int);
}
pub closed spec fn even_state_0_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_0_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+67108864int*c[1]+4194304int*c[2]+262144int*c[3]+16384int*c[4]+1024int*c[5]}
pub closed spec fn even_state_0_2(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+268435456int*c[1]+67108864int*c[2]+16777216int*c[3]+4194304int*c[4]+1048576int*c[5]}
pub closed spec fn even_state_0_3(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+1073741824int*c[1]+1073741824int*c[2]+1073741824int*c[3]+1073741824int*c[4]+1073741824int*c[5]}
pub closed spec fn even_state_0_4(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+4294967296int*c[1]+17179869184int*c[2]+68719476736int*c[3]+274877906944int*c[4]+1099511627776int*c[5]}
pub closed spec fn even_state_0_5(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+17179869184int*c[1]+274877906944int*c[2]+4398046511104int*c[3]+70368744177664int*c[4]+1125899906842624int*c[5]}
pub closed spec fn even_state_1_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_1_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_1_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+5242880int*c[2]+1376256int*c[3]+348160int*c[4]+87296int*c[5]}
pub closed spec fn even_state_1_3(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+20971520int*c[2]+22020096int*c[3]+22282240int*c[4]+22347776int*c[5]}
pub closed spec fn even_state_1_4(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+83886080int*c[2]+352321536int*c[3]+1426063360int*c[4]+5721030656int*c[5]}
pub closed spec fn even_state_1_5(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+335544320int*c[2]+5637144576int*c[3]+91268055040int*c[4]+1464583847936int*c[5]}
pub closed spec fn even_state_2_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_2_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_2_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_2_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+344064int*c[3]+365568int*c[4]+371008int*c[5]}
pub closed spec fn even_state_2_4(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+1376256int*c[3]+5849088int*c[4]+23744512int*c[5]}
pub closed spec fn even_state_2_5(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+5505024int*c[3]+93585408int*c[4]+1519648768int*c[5]}
pub closed spec fn even_state_3_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_3_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_3_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_3_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub closed spec fn even_state_3_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+21760int*c[4]+92752int*c[5]}
pub closed spec fn even_state_3_5(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+87040int*c[4]+1484032int*c[5]}
pub closed spec fn even_state_4_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_4_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_4_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_4_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub closed spec fn even_state_4_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+341int*c[5]}
pub closed spec fn even_state_4_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1364int*c[5]}
pub closed spec fn even_state_5_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_5_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_5_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_5_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub closed spec fn even_state_5_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+341int*c[5]}
pub closed spec fn even_state_5_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_6_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_6_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_6_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_6_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+5440int*c[4]+5797int*c[5]}
pub closed spec fn even_state_6_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+85int*c[5]}
pub closed spec fn even_state_6_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_7_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_7_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_7_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+86016int*c[3]+22848int*c[4]+5797int*c[5]}
pub closed spec fn even_state_7_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+1344int*c[4]+357int*c[5]}
pub closed spec fn even_state_7_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+21int*c[5]}
pub closed spec fn even_state_7_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_8_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_8_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+1310720int*c[2]+86016int*c[3]+5440int*c[4]+341int*c[5]}
pub closed spec fn even_state_8_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+20480int*c[3]+1344int*c[4]+85int*c[5]}
pub closed spec fn even_state_8_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+320int*c[4]+21int*c[5]}
pub closed spec fn even_state_8_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+5int*c[5]}
pub closed spec fn even_state_8_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_9_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_9_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_9_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_9_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]+64int*c[4]+1int*c[5]}
pub closed spec fn even_state_9_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]+1int*c[5]}
pub closed spec fn even_state_9_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_10_0(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[0]}
pub closed spec fn even_state_10_1(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[1]}
pub closed spec fn even_state_10_2(c:Seq<int>)->int recommends c.len()==7 {262144int*c[2]}
pub closed spec fn even_state_10_3(c:Seq<int>)->int recommends c.len()==7 {4096int*c[3]}
pub closed spec fn even_state_10_4(c:Seq<int>)->int recommends c.len()==7 {64int*c[4]}
pub closed spec fn even_state_10_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn even_state_11_0(c:Seq<int>)->int recommends c.len()==7 {1int*c[0]}
pub closed spec fn even_state_11_1(c:Seq<int>)->int recommends c.len()==7 {1int*c[1]}
pub closed spec fn even_state_11_2(c:Seq<int>)->int recommends c.len()==7 {1int*c[2]}
pub closed spec fn even_state_11_3(c:Seq<int>)->int recommends c.len()==7 {1int*c[3]}
pub closed spec fn even_state_11_4(c:Seq<int>)->int recommends c.len()==7 {1int*c[4]}
pub closed spec fn even_state_11_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn odd_state_0_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_0_1(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+4294967296int*c[1]+268435456int*c[2]+16777216int*c[3]+1048576int*c[4]+65536int*c[5]+4096int*c[6]}
pub closed spec fn odd_state_0_2(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+17179869184int*c[1]+4294967296int*c[2]+1073741824int*c[3]+268435456int*c[4]+67108864int*c[5]+16777216int*c[6]}
pub closed spec fn odd_state_0_3(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+68719476736int*c[1]+68719476736int*c[2]+68719476736int*c[3]+68719476736int*c[4]+68719476736int*c[5]+68719476736int*c[6]}
pub closed spec fn odd_state_0_4(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+274877906944int*c[1]+1099511627776int*c[2]+4398046511104int*c[3]+17592186044416int*c[4]+70368744177664int*c[5]+281474976710656int*c[6]}
pub closed spec fn odd_state_0_5(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1099511627776int*c[1]+17592186044416int*c[2]+281474976710656int*c[3]+4503599627370496int*c[4]+72057594037927936int*c[5]+1152921504606846976int*c[6]}
pub closed spec fn odd_state_0_6(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+4398046511104int*c[1]+281474976710656int*c[2]+18014398509481984int*c[3]+1152921504606846976int*c[4]+73786976294838206464int*c[5]+4722366482869645213696int*c[6]}
pub closed spec fn odd_state_1_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_1_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_1_2(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+335544320int*c[2]+88080384int*c[3]+22282240int*c[4]+5586944int*c[5]+1397760int*c[6]}
pub closed spec fn odd_state_1_3(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+1342177280int*c[2]+1409286144int*c[3]+1426063360int*c[4]+1430257664int*c[5]+1431306240int*c[6]}
pub closed spec fn odd_state_1_4(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+5368709120int*c[2]+22548578304int*c[3]+91268055040int*c[4]+366145961984int*c[5]+1465657589760int*c[6]}
pub closed spec fn odd_state_1_5(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+21474836480int*c[2]+360777252864int*c[3]+5841155522560int*c[4]+93733366267904int*c[5]+1500833371914240int*c[6]}
pub closed spec fn odd_state_1_6(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+85899345920int*c[2]+5772436045824int*c[3]+373833953443840int*c[4]+23995741764583424int*c[5]+1536853372840181760int*c[6]}
pub closed spec fn odd_state_2_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_2_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_2_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_2_3(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+22020096int*c[3]+23396352int*c[4]+23744512int*c[5]+23831808int*c[6]}
pub closed spec fn odd_state_2_4(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+88080384int*c[3]+374341632int*c[4]+1519648768int*c[5]+6100942848int*c[6]}
pub closed spec fn odd_state_2_5(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+352321536int*c[3]+5989466112int*c[4]+97257521152int*c[5]+1561841369088int*c[6]}
pub closed spec fn odd_state_2_6(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1409286144int*c[3]+95831457792int*c[4]+6224481353728int*c[5]+399831390486528int*c[6]}
pub closed spec fn odd_state_3_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_3_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_3_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_3_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_3_4(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+1392640int*c[4]+5936128int*c[5]+24115520int*c[6]}
pub closed spec fn odd_state_3_5(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+5570560int*c[4]+94978048int*c[5]+1543393280int*c[6]}
pub closed spec fn odd_state_3_6(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+22282240int*c[4]+1519648768int*c[5]+98777169920int*c[6]}
pub closed spec fn odd_state_4_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_4_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_4_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_4_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_4_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_4_5(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+87296int*c[5]+1489488int*c[6]}
pub closed spec fn odd_state_4_6(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+349184int*c[5]+23831808int*c[6]}
pub closed spec fn odd_state_5_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_5_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_5_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_5_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_5_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_5_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_5_6(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5460int*c[6]}
pub closed spec fn odd_state_6_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_6_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_6_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_6_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_6_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_6_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_6_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_7_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_7_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_7_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_7_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_7_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+21824int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_7_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+341int*c[6]}
pub closed spec fn odd_state_7_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_8_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_8_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_8_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_8_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+348160int*c[4]+371008int*c[5]+376805int*c[6]}
pub closed spec fn odd_state_8_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+5440int*c[5]+5797int*c[6]}
pub closed spec fn odd_state_8_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+85int*c[6]}
pub closed spec fn odd_state_8_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_9_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_9_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_9_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+5505024int*c[3]+1462272int*c[4]+371008int*c[5]+93093int*c[6]}
pub closed spec fn odd_state_9_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+86016int*c[4]+22848int*c[5]+5797int*c[6]}
pub closed spec fn odd_state_9_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+1344int*c[5]+357int*c[6]}
pub closed spec fn odd_state_9_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+21int*c[6]}
pub closed spec fn odd_state_9_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_10_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_10_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+83886080int*c[2]+5505024int*c[3]+348160int*c[4]+21824int*c[5]+1365int*c[6]}
pub closed spec fn odd_state_10_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+1310720int*c[3]+86016int*c[4]+5440int*c[5]+341int*c[6]}
pub closed spec fn odd_state_10_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+20480int*c[4]+1344int*c[5]+85int*c[6]}
pub closed spec fn odd_state_10_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+320int*c[5]+21int*c[6]}
pub closed spec fn odd_state_10_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+5int*c[6]}
pub closed spec fn odd_state_10_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_11_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]+64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]+1int*c[6]}
pub closed spec fn odd_state_11_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_12_0(c:Seq<int>)->int recommends c.len()==7 {68719476736int*c[0]}
pub closed spec fn odd_state_12_1(c:Seq<int>)->int recommends c.len()==7 {1073741824int*c[1]}
pub closed spec fn odd_state_12_2(c:Seq<int>)->int recommends c.len()==7 {16777216int*c[2]}
pub closed spec fn odd_state_12_3(c:Seq<int>)->int recommends c.len()==7 {262144int*c[3]}
pub closed spec fn odd_state_12_4(c:Seq<int>)->int recommends c.len()==7 {4096int*c[4]}
pub closed spec fn odd_state_12_5(c:Seq<int>)->int recommends c.len()==7 {64int*c[5]}
pub closed spec fn odd_state_12_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
pub closed spec fn odd_state_13_0(c:Seq<int>)->int recommends c.len()==7 {1int*c[0]}
pub closed spec fn odd_state_13_1(c:Seq<int>)->int recommends c.len()==7 {1int*c[1]}
pub closed spec fn odd_state_13_2(c:Seq<int>)->int recommends c.len()==7 {1int*c[2]}
pub closed spec fn odd_state_13_3(c:Seq<int>)->int recommends c.len()==7 {1int*c[3]}
pub closed spec fn odd_state_13_4(c:Seq<int>)->int recommends c.len()==7 {1int*c[4]}
pub closed spec fn odd_state_13_5(c:Seq<int>)->int recommends c.len()==7 {1int*c[5]}
pub closed spec fn odd_state_13_6(c:Seq<int>)->int recommends c.len()==7 {1int*c[6]}
}
