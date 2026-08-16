from fastapi.testclient import TestClient
from market_xray.app import app

client = TestClient(app)

def test_market_registry_contains_watchlist():
    r = client.get('/api/v1/markets')
    assert r.status_code == 200
    names = set(r.json()['markets'])
    assert names == {'NAS100','SPX500','EURUSD','GBPUSD','XAUUSD','XAGUSD','USOIL','DXY','BTCUSD','ETHUSD'}

def test_unknown_market_is_rejected():
    assert client.get('/api/v1/xray/NOPE').status_code == 404

def test_trade_flow_derives_control():
    base = 1_800_000_000_000_000_000
    for i, qty in enumerate([10, 20, 30], start=1):
        r = client.post('/api/v1/events', json={
            'market':'NAS100','ts_ns':base+i,'kind':'trade','price':20000+i,
            'qty':qty,'side':'buy','sequence':i,'venue':'TEST'
        })
        assert r.status_code == 200
    r = client.get('/api/v1/xray/NAS100?limit=100')
    body = r.json()
    assert body['state']['control'] == 'BUYERS'
    assert body['state']['evidence'] == 'derived'
    assert body['data_health']['verified'] is True
