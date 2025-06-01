from flask import Flask, render_template, request, session, make_response, redirect, url_for
import xml.etree.ElementTree as et
import json
import io # For handling string as file-like object if needed

app = Flask(__name__)
app.secret_key = "your_very_secret_key_for_session_management" # Important: Change this in production

# --- Your script's logic, slightly adapted for Flask ---
DEPNAME = 'evolution' # For the output filename

KNOWN_REMOTES = {
    "github-non-los": "https://github.com",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
    "aosp": "https://android.googlesource.com",
    "github": "..", # This might need special handling or clarification if base URL changes
    "private": "ssh://git@github.com",
    "evo": "https://github.com/Evolution-X",
    "evo-devices": "https://github.com/Evolution-X-Devices",
    "evo-bitbucket": "https://bitbucket.com/evo-x",
    "evo-main": "https://git.mainlining.org/EvolutionX",
    "evo-gitlab": "https://gitlab.com/EvoX",
    "evo-codeberg": "https://codeberg.org/Evolution-X",
}

# These will be reset per request
# To manage state within a request, we can pass them around or use a class instance.
# For simplicity, we'll make them part of a processing context for each request.

def sort_dict_logic(d: dict) -> dict:
    ord_keys = [
        'repository',
        'target_path',
        'branch',
        'remote',
        'clone_depth'
    ]
    u = {}
    for k in ord_keys:
        if k in d:
            u[k] = d[k]
    # Add any other keys that were not in ord_keys but were in d
    for k in d:
        if k not in u:
            u[k] = d[k]
    return u

def format_dict_logic(d: dict, current_xml_remotes: dict) -> dict:
    p = {
        'name': 'repository',
        'path': 'target_path',
        'remote': 'remote',
        'revision': 'branch',
        'clone-depth': 'clone_depth'
    }
    ans = {}
    for x_key_original, x_val in d.items():
        if x_key_original in p.keys():
            new_key = p[x_key_original]
            if x_key_original == 'remote':
                remote_name_in_project = x_val
                # Case 1: The remote attribute in <project> refers to a <remote> tag defined in the XML
                if remote_name_in_project in current_xml_remotes:
                    fetch_url = current_xml_remotes[remote_name_in_project]
                    found_known_shortname = False
                    for known_shortname, known_url in KNOWN_REMOTES.items():
                        if fetch_url == known_url:
                            ans[new_key] = known_shortname
                            found_known_shortname = True
                            break
                    if not found_known_shortname:
                        ans[new_key] = remote_name_in_project # Use the name from XML's <remote name="this_name">
                # Case 2: The remote attribute in <project> refers directly to a KNOWN_REMOTES shortname
                elif remote_name_in_project in KNOWN_REMOTES:
                    ans[new_key] = remote_name_in_project
                # Case 3: Unknown remote
                else:
                    ans[new_key] = '!!!!!!idk_remote_not_in_xml_or_known_remotes'
            else:
                ans[new_key] = x_val
        # Keep other attributes not in p as they are (e.g. 'groups')
        # else:
        #     ans[x_key_original] = x_val # If you want to keep ALL original attributes
                                      # Your original SortDict would filter them out unless added to ord_keys
    return sort_dict_logic(ans)

def process_xml_data(xml_string: str):
    """
    Parses XML string and returns structured data, discovered remotes, and other tags.
    """
    projects_list = []
    discovered_xml_remotes = {} # Remotes defined within the XML (<remote name="..." fetch="..." />)
    other_tags_data = []

    try:
        root = et.fromstring(xml_string)
        for entry in root:
            tag, attribs = entry.tag, entry.attrib
            if tag == 'remote':
                if 'name' in attribs and 'fetch' in attribs:
                    discovered_xml_remotes[attribs['name']] = attribs['fetch']
            elif tag == 'project':
                # Pass discovered_xml_remotes for context, as project formatting might depend on it
                projects_list.append(format_dict_logic(attribs, discovered_xml_remotes))
            else:
                # Store other tags with their attributes
                other_info = {'tag_name': tag}
                other_info.update(attribs)
                other_tags_data.append(other_info)

        # Prepare final structured data
        final_data_for_json = []
        if other_tags_data:
            # You might want a specific structure for these
            # For now, adding them as a special entry or list of entries
            final_data_for_json.append({'type': 'other_xml_tags', 'details': other_tags_data})

        final_data_for_json.extend(projects_list)

        return final_data_for_json, discovered_xml_remotes, None # data, remotes, error
    except et.ParseError as e:
        return None, None, f"XML Parse Error: {e}"
    except Exception as e:
        return None, None, f"An unexpected error occurred: {e}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        xml_content = ""
        error_message = None
        
        if 'xmlfile' in request.files and request.files['xmlfile'].filename != '':
            xml_file = request.files['xmlfile']
            if xml_file.content_type in ['text/xml', 'application/xml']:
                try:
                    xml_content = xml_file.read().decode('utf-8')
                except Exception as e:
                    error_message = f"Error reading uploaded file: {e}"
            else:
                error_message = "Invalid file type. Please upload an XML file."
        elif 'xmltext' in request.form and request.form['xmltext'].strip() != '':
            xml_content = request.form['xmltext'].strip()
        else:
            error_message = "No XML input provided. Please upload a file or paste XML content."

        if not error_message and xml_content:
            processed_data, discovered_remotes, parse_error = process_xml_data(xml_content)
            if parse_error:
                error_message = parse_error
                return render_template('index.html', error=error_message, known_remotes=KNOWN_REMOTES)
            
            session['processed_data_for_json'] = processed_data # Store for download
            return render_template('index.html', 
                                   projects=processed_data, 
                                   formatted_projects=str(json.dumps(processed_data, indent=2)),
                                   xml_remotes=discovered_remotes,
                                   known_remotes=KNOWN_REMOTES,
                                   has_results=True)
        else:
            return render_template('index.html', error=error_message or "Processing error.", known_remotes=KNOWN_REMOTES)
            
    # GET request
    return render_template('index.html', known_remotes=KNOWN_REMOTES)

@app.route('/download_dependencies')
def download_dependencies():
    if 'processed_data_for_json' not in session:
        return "No data to download. Please process an XML file first.", 404

    data_to_download = session['processed_data_for_json']
    json_output = json.dumps(data_to_download, indent=2)
    
    response = make_response(json_output)
    response.headers['Content-Disposition'] = f'attachment; filename={DEPNAME}.dependencies'
    response.headers['Content-Type'] = 'application/json'

    return response

if __name__ == '__main__':
    app.run(debug=True)
