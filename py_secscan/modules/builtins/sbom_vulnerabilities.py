import argparse
import json
import os

import requests

from py_secscan import stdx


# Schema: https://google.github.io/osv.dev/post-v1-query/
OSV_API_V1_URL = "https://api.osv.dev/v1/query"


def osv_get_package_cve(package_name, version=None):
    data = {"version": version, "package": {"name": package_name, "ecosystem": "PyPI"}}
    cves = []
    stdx.info(f"[OSV] Scanning package: {package_name}=={version}")

    try:
        response = requests.post(OSV_API_V1_URL, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        stdx.exception(e, f"Failed to get vulnerabilities for package: {package_name}=={version}")

    vulnerabilities = response.json().get("vulns", [])
    for vulnerability in vulnerabilities:
        cve = {
            "bom-ref": f"{package_name}=={version}",
            "id": vulnerability.get("id"),
            "aliases": vulnerability.get("aliases"),
            "published": vulnerability.get("published"),
            "updated": vulnerability.get("modified"),
            "description": vulnerability.get("summary"),
            "detail": vulnerability.get("details"),
            "severity": vulnerability.get("severity"),
            "references": [
                {"id": reference["type"], "source": {"url": reference["url"]}}
                for reference in vulnerability.get("references", [])
            ],
            "affects": [
                {
                    "ranges": affected.get("ranges", []),
                    "versions": affected.get("versions", []),
                    "database_specific": affected.get("database_specific", []),
                }
                for affected in vulnerability.get("affected", [])
                if affected["package"]["name"] == package_name
            ],
        }
        cves.append(cve)

    return cves


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("sbom_filepath", type=str, help="SBOM file path")
        parser.add_argument(
            "vulnerabilities_output_filename",
            type=str,
            help="Vulnerabilities output file path",
        )

        args = parser.parse_args()

        if not os.path.isfile(args.sbom_filepath):
            stdx.exception(FileNotFoundError(f"File not found: {args.sbom_filepath}"))

        with open(args.sbom_filepath) as f:
            sbom = json.loads(f.read())

        packages_cve = {}
        for component in sbom["components"]:
            name = component["name"]
            version = component["version"]
            packages_cve[name] = osv_get_package_cve(name, version)

        with open(args.vulnerabilities_output_filename, "w") as f:
            f.write(json.dumps(packages_cve, indent=2))
            f.write("\n")
    except KeyboardInterrupt:
        stdx.error("Manual interruption")


if __name__ == "__main__":
    main()
