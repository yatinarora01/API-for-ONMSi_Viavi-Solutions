import requests
import xmltodict
import json
from flask import Flask, Response
from requests.auth import HTTPBasicAuth
import concurrent.futures

ONMSI_BASE = "http://10.33.20.218/rs"
USER = "admin"
PASSWORD = "password"

app = Flask(__name__)
session = requests.Session()
session.auth = HTTPBasicAuth(USER, PASSWORD)

def fetch_detail(url):
    r = session.get(url)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        return xmltodict.parse(r.content)

@app.route('/', methods=["GET"])
def home():
    return "Welcome to the ONMSi Fiber Remote Testing Solution!"

@app.route("/rs/otus/full", methods=["GET"])
def otus_full():
    # 1) fetch summary list
    r1 = session.get(f"{ONMSI_BASE}/otus/all")
    r1.raise_for_status()
    try:
        root = r1.json()  # Try to parse as JSON
    except ValueError:
        root = xmltodict.parse(r1.content)  # Parse as XML if JSON fails

    # 2) parallel fetch of every detail
    keys = [e["internalKey"] for e in root["ns2:EntityList"]["entities"]]
    otu_details = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_detail, f"{ONMSI_BASE}/otus/{key}"): key for key in keys}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                otu_data = future.result()
                otu_details.append(otu_data)
            except Exception as e:
                print(f"Error fetching details for OTU {key}: {e}")

    # 3) fetch details for each internal key within each OTU
    expanded_otu_details = []
    for otu in otu_details:
        otu_data = otu["ns2:Otu"]
        otu_data["otdrs_detail"] = []
        otu_data["switches_detail"] = []
        otu_data["ports_detail"] = []
        otu_data["links_detail"] = []

        if "otdrs" in otu_data and isinstance(otu_data["otdrs"], list):
            for otdr in otu_data["otdrs"]:
                otdr_detail = fetch_detail(f"{ONMSI_BASE}/otus/{otdr['internalKey']}")
                otu_data["otdrs_detail"].append(otdr_detail)

        if "switches" in otu_data and isinstance(otu_data["switches"], list):
            for switch in otu_data["switches"]:
                switch_detail = fetch_detail(f"{ONMSI_BASE}/otus/{switch['internalKey']}")
                otu_data["switches_detail"].append(switch_detail)

        # Fetch ports details
        ports_detail = fetch_detail(f"{ONMSI_BASE}/otus/{otu_data['internalKey']}/ports")
        otu_data["ports_detail"].append(ports_detail)

        # Fetch links details
        links_summary = fetch_detail(f"{ONMSI_BASE}/links/all")
        link_keys = [link["internalKey"] for link in links_summary["ns2:EntityList"]["entities"]]
        link_details = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(fetch_detail, f"{ONMSI_BASE}/links/{key}"): key for key in link_keys}
            for future in concurrent.futures.as_completed(futures):
                key = futures[future]
                try:
                    link_data = future.result()
                    link_details.append(link_data)
                except Exception as e:
                    print(f"Error fetching details for link {key}: {e}")

        otu_data["links_detail"] = link_details

        expanded_otu_details.append(otu_data)

    # 4) build single response
    merged = {"summary": root, "details": expanded_otu_details}
    return Response(
        response=json.dumps(merged, indent=2),
        status=200,
        mimetype="application/json"
    )

if __name__ == "__main__":
    # run on port 5004 – keep VPN active
    app.run(host="0.0.0.0", port=5004)