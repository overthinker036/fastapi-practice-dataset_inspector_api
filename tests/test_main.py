from fastapi.testclient import TestClient
from main import app
from test_config import client


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200

#Tests for POST /analysis:
#User sends CSV files. What things can go wrong?
#1. Type: Not a CSV
#2. Size: Empty, Oversized, Correct Sized

def test_not_a_csv(client):
    response = client.post(
        "/analyses",
        files = {
            "file" : ("file.txt", b"I am a human", "text/text")
        }
    )

    assert response.status_code == 415

def test_valid_csv(client):
    csv_data = b"""Name, Age, City
    Alice, 20, Dhaka
    Bob,,Chattogram
    Charlie, 25,
    """
    response = client.post(
        "/analyses",
        files = {
            "file" : ("file.csv", csv_data, "text/csv")
        }
    )

    assert response.status_code == 202



def test_empty_csv(client):
    response = client.post(
        "/analyses",
        files = {
            "file": ("empty.csv", b"", "text/csv")
        }
    )

    assert response.status_code == 400

def test_oversized_csv(client):
    oversized_csv_data = b"a" * ((2*1024*1024)+1)
    response = client.post("/analyses", 
        files={
            "file": ("large.csv", oversized_csv_data,"text/csv")
        }
    )
    assert response.status_code == 413


