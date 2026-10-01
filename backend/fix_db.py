import sqlite3
import json

conn = sqlite3.connect('/Users/srisaran/Quads/backend/quads_checkpoints.db')
cursor = conn.cursor()
cursor.execute("SELECT thread_id, checkpoint_id, checkpoint FROM checkpoints")
rows = cursor.fetchall()
for row in rows:
    try:
        cp = json.loads(row[2])
        if 'channel_values' in cp and 'state' in cp['channel_values']:
            state = cp['channel_values']['state']
            if 'case_data' in state and 'status' in state['case_data']:
                status = state['case_data']['status']
                if status == 'DECISION_PENDING':
                    state['case_data']['completed_stages'] = ["CASE", "IMPACT", "PRIORITY"]
                    cursor.execute("UPDATE checkpoints SET checkpoint = ? WHERE thread_id = ? AND checkpoint_id = ?", (json.dumps(cp), row[0], row[1]))
    except Exception as e:
        print(e)
conn.commit()
conn.close()
