import random
import string

honey_accounts = []

@app.post("/honey/generate")
def generate_honey_accounts():
    honey_accounts.clear()
    for i in range(5):
        fake = {
            "site": f"fake_site_{i}",
            "username": f"user{i}",
            "password": ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        }
        honey_accounts.append(fake)

    return {"status": "generated", "accounts": honey_accounts}


@app.get("/honey/view")
def view_honey_accounts():
    return {"accounts": honey_accounts}
