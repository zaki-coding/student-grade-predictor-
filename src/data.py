"""Download the original UCI archive and preserve source provenance."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile
import pandas as pd
from src.schema import FEATURES, SPECS

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'student-por.csv'
SOURCE_URL = 'https://archive.ics.uci.edu/static/public/320/student+performance.zip'
EXPECTED_CSV_SHA256 = 'a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f'


def _extract_csv(content):
    with ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            if name.endswith('student-por.csv'):
                return archive.read(name)
        for name in archive.namelist():
            if name.endswith('student.zip'):
                return _extract_csv(archive.read(name))
    raise ValueError('UCI archive did not contain student-por.csv.')


def validate_dataset(frame):
    required = FEATURES['updated'] + ['G3']
    if len(frame) != 649 or not set(required) <= set(frame.columns):
        raise ValueError('Expected original 649-row Portuguese UCI dataset with all required columns.')
    for field in required:
        values = frame[field].dropna()
        spec = SPECS.get(field, {'min': 0, 'max': 20})
        if 'options' in spec:
            if not values.isin(spec['options']).all():
                raise ValueError(f'Unexpected category in {field}.')
        else:
            if not pd.api.types.is_numeric_dtype(values) or not values.between(spec['min'], spec['max']).all() or not (values % 1 == 0).all():
                raise ValueError(f'Invalid dataset values for {field}.')
    if frame['G3'].isna().any():
        raise ValueError('Target grades cannot be missing.')
    return frame


def load_data(download=True):
    if not DATA_PATH.exists():
        if not download:
            raise FileNotFoundError('Dataset unavailable. Run python -m src.train to download it.')
        request = Request(SOURCE_URL, headers={'User-Agent': 'StudentSuccessAI/1.0 educational research'})
        with urlopen(request, timeout=60) as response:
            payload = response.read()
        csv_bytes = _extract_csv(payload)
        if hashlib.sha256(csv_bytes).hexdigest() != EXPECTED_CSV_SHA256:
            raise ValueError('Official dataset content changed; inspect the source before updating the pinned checksum.')
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_bytes(csv_bytes)
        provenance = {
            'source': SOURCE_URL, 'dataset': 'Student Performance; Portuguese subject only',
            'citation': 'Cortez, P. (2008). Student Performance [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5TG7T',
            'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'archive_sha256': hashlib.sha256(payload).hexdigest(),
            'csv_sha256': hashlib.sha256(csv_bytes).hexdigest(),
        }
        DATA_PATH.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    if hashlib.sha256(DATA_PATH.read_bytes()).hexdigest() != EXPECTED_CSV_SHA256:
        raise ValueError('Dataset checksum does not match the pinned original Portuguese dataset.')
    provenance_path = DATA_PATH.with_suffix('.provenance.json')
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
        actual_hash = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
        if actual_hash != provenance['csv_sha256']:
            raise ValueError('Dataset checksum differs from downloaded source provenance.')
    return validate_dataset(pd.read_csv(DATA_PATH, sep=';'))
