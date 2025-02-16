import argparse
import json
import os
import sys

import pandas as pd
import streamlit as st

from py_secscan import process, stdx


def sbom(sbom_filepath: str = None):  # noqa: C901
    @st.dialog("Cast your vote")
    def display_package_more_info(component):
        if component["purl"].startswith("pkg:pypi"):
            url = f"[{component['purl']}](https://pypi.org/project/{component['name']})"
        else:
            url = component["purl"]

        st.write(f"**Bom ref:** {component['bom-ref']}")
        st.write(f"**Url:** {url}")
        st.write(f"**Type:** {component['type'].title()}")
        st.write(f"**Description:** {component.get('description', 'N/A')}")
        if "externalReferences" in component:
            st.write("**External References:**")
            for ref in component["externalReferences"]:
                st.write(f"- [{ref.get('comment', 'Link')}]({ref['url']})")
        # Add other details as needed...

        st.markdown("---")

    st.header("Software Bill of Materials (SBOM)")

    json_data = {}

    if sbom_filepath and os.path.isfile(sbom_filepath):
        with open(sbom_filepath) as f:
            json_data = json.load(f)

    uploaded_file = st.file_uploader("Upload SBOM JSON file", type="json")

    if uploaded_file is not None:
        try:
            json_data = json.load(uploaded_file)
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")

    st.header("General Information")
    st.write(f"**Filepath**: {sbom_filepath if sbom_filepath else uploaded_file.name}")
    st.write(f"**Serial Number**: {json_data.get('serialNumber', 'N/A')}")
    st.write(f"**Version**: {json_data.get('version', 'N/A')}")
    st.write(f"**Spec Version**: {json_data.get('specVersion', 'N/A')}")
    st.write(f"**Schema**: {json_data.get('$schema', 'N/A')}")
    st.write(f"**Format**: {json_data.get('bomFormat', 'N/A')}")

    st.header("Components")

    for component in json_data["components"]:
        package_name, package_version, package_license, package_details = st.columns(4)

        with package_name:
            st.write(f"**{component['name']}**")
        with package_version:
            st.write(f"v{component['version']}")
        with package_license:
            licenses = component.get("licenses", [])
            license_str = ""
            for lic in licenses:
                if "license" in lic and "id" in lic["license"]:
                    license_str += lic["license"]["id"] + ", "
                elif "expression" in lic:
                    license_str += lic["expression"] + ", "
                elif "license" in lic and "name" in lic["license"]:
                    license_str += lic["license"]["name"] + ", "
            st.write(license_str.rstrip(", "))
        with package_details:
            if st.button("Details", key=component["bom-ref"]):
                display_package_more_info(component)


def sbom_vulnerabilities(vulnerabilities_filepath: str = None):  # noqa: C901
    def vulnerability_chart(vulnerability_data):
        st.header("Vulnerability Distribution")

        df = pd.DataFrame(
            list(vulnerability_data.items()),
            columns=["Packages", "Vulnerabilities Count"],
        )

        st.bar_chart(df, x="Packages", y="Vulnerabilities Count", use_container_width=True)

    def process_json(json_data):
        processed_data = []

        for package, details in json_data.items():
            if details:
                for issue in details:
                    references = [ref["source"]["url"] for ref in issue.get("references", [])[:3]]
                    processed_data.append(
                        {
                            "Package": package,
                            "ID": issue.get("id", "N/A"),
                            "Description": issue.get("description", "N/A"),
                            "Fixed in": issue.get("affects", [{}])[0]
                            .get("ranges", [{}])[0]
                            .get("events", [{}])[-1]
                            .get("fixed", "N/A"),
                            "References": references[0] if references else None,
                            "Details": issue.get("detail", "N/A"),
                        }
                    )

        return pd.DataFrame(processed_data)

    uploaded_file = st.file_uploader("📂 Upload the JSON vulnerability file", type=["json"])

    json_data = {}

    if vulnerabilities_filepath and os.path.isfile(vulnerabilities_filepath):
        with open(vulnerabilities_filepath) as f:
            json_data = json.load(f)

    if uploaded_file is not None:
        try:
            json_data = json.load(uploaded_file)
            st.success("✅ JSON file successfully loaded!")
        except Exception as e:
            st.error("❌ Error reading the JSON file.")
            st.error(str(e))

    if json_data is None:
        st.info("🔄 Waiting for a JSON file...")
        return

    data = process_json(json_data)
    if data.empty:
        st.warning("No vulnerabilities found in the SBOM file.")
        return

    st.dataframe(
        data,
        use_container_width=True,
        column_config={"References": st.column_config.LinkColumn()},
    )
    vulnerability_chart(
        {package: len(vulnerabilities) for package, vulnerabilities in json_data.items() if len(vulnerabilities) > 0}
    )


def argparser(parser: argparse.ArgumentParser = None) -> argparse.Namespace:
    if not parser:
        parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--sbom-filepath", type=str, default="sbom.json", help="SBOM file path")
    parser.add_argument(
        "-v",
        "--vulnerabilities-filepath",
        type=str,
        default="sbom_vulnerabilities.json",
        help="SBOM Vulnerabilities file path",
    )
    return parser


def main():
    args = argparser().parse_args()

    if not os.path.isfile(args.sbom_filepath) or not os.path.isfile(args.vulnerabilities_filepath):
        stdx.error("SBOM or Vulnerabilities file not found.")
        return 1

    st.set_page_config(page_title="SBOM Vulnerabilities Viewer", layout="wide")
    st.title("🚀 PySecScan - Vulnerabilities Viewer")

    tab_sbom, tab_sbom_vulnerabilities = st.tabs(["SBOM", "Vulnerabilities"])

    with tab_sbom:
        sbom(sbom_filepath=args.sbom_filepath)
    with tab_sbom_vulnerabilities:
        sbom_vulnerabilities(vulnerabilities_filepath=args.vulnerabilities_filepath)


def start(sbom_filepath: str, vulnerabilities_filepath: str):
    try:
        process.run_subprocess(
            f"streamlit run \
                {__file__} \
                -- \
                -s {sbom_filepath} \
                -v {vulnerabilities_filepath}",
        )
    except KeyboardInterrupt:
        stdx.error("Manual interruption")


if __name__ == "__main__":
    sys.exit(main())
