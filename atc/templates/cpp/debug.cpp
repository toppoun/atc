#include <bits/stdc++.h>
using namespace std;

using ll = long long;

const int INF = 1e9;
const ll LINF = 1e18;
const int MOD = 1e9 + 7;
const int MOD2 = 998244353;

#define rep(i, n) for (int i = 0; i < (int)(n); i++)
#define all(x) (x).begin(), (x).end()

template<class T>
void dbg_one(const char* name, const T& value) {
    cerr << name << " = " << value << '\n';
}

#define dbg(x) dbg_one(#x, x)

void solve() {
    int n;
    cin >> n;
    dbg(n);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    solve();
    return 0;
}
