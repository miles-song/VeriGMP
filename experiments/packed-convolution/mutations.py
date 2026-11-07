"""False model changes that the complete focused verifier must reject."""
MUTATIONS = {
    'undersized-radix': ('requires p>0, shorter(a,c)<=pow(2,g), w>=2*p+g,',
                         'requires p>0, shorter(a,c)<=pow(2,g), w>=p+g,'),
    'extract-next-slot': ('(packed(a,b)/power(b,k))%b==a[k as int],',
                          '(packed(a,b)/power(b,k+1))%b==a[k as int],'),
    'omit-last-summand': ('convolution_prefix(a, c, k, a.len())',
                          'convolution_prefix(a, c, k, if a.len()==0 {0} else {(a.len()-1) as nat})'),
    'truncate-one-too-soon': ('a.take(if d < a.len() { d as int } else { a.len() as int })',
                            'a.take(if d < a.len() { if d==0 {0} else {(d-1) as int} } else { a.len() as int })'),
}
