import importlib.metadata as metadata
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
def version(name):
    try:return metadata.version(name)
    except metadata.PackageNotFoundError:return None
data=dict(python=sys.version,executable=sys.executable,
          packages={name:version(name) for name in
                    ['numpy','scipy','opencv-contrib-python','pandas','arcade','pymunk']})
(root/'ENVIRONMENT.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
