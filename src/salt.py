import hashlib


def get_student_params(student_id: str):
    h = int(hashlib.sha256(student_id.encode('utf-8')).hexdigest()[:8], 16)
    return {'student_id': student_id, 'N': 1024 + (h % 9) * 64,
            'buffer_elements': 16_777_216, 'seed': h % 100_007}

