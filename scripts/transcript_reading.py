"""Build a word-preserving reading copy from ASR boundaries."""
import json
import re
import unicodedata
from pathlib import Path


def words(text):
    return ''.join(c for c in text if not c.isspace() and not unicodedata.category(c).startswith('P'))


def enrich(payload):
    analyses = {str(a.get('referenceId')): a for a in payload.get('workAnalyses', [])}
    for work_id, sections in payload.get('transcriptSections', {}).items():
        analysis = analyses.get(str(work_id), {})
        try:
            utterances = json.loads(Path(analysis.get('asrMetadataPath', '')).read_text()).get('utterances', [])
        except (OSError, ValueError):
            utterances = []
        for section in sections:
            raw = section.get('text', '')
            if section.get('readingText') and words(section['readingText']) == words(raw):
                continue
            # Locate exact ASR chunks in the original section; never substitute words.
            boundaries = set()
            cursor = 0
            for utterance in utterances:
                chunk = str(utterance.get('text', '')).strip()
                if not chunk:
                    continue
                start = raw.find(chunk, cursor)
                if start >= 0:
                    cursor = start + len(chunk)
                    boundaries.add(cursor)
            result = []
            sentence_length = 0
            sentences = 0
            for index, char in enumerate(raw, 1):
                result.append(char)
                sentence_length += 1
                if char in '。！？!?':
                    sentence_length = 0
                    sentences += 1
                if index not in boundaries or index == len(raw):
                    continue
                if unicodedata.category(char).startswith('P') or unicodedata.category(raw[index]).startswith('P'):
                    continue
                if sentence_length >= 55:
                    result.append('。')
                    sentence_length = 0
                    sentences += 1
                    if sentences % 3 == 0:
                        result.append('\n\n')
                else:
                    result.append('，')
            reading = ''.join(result).strip()
            if reading and reading[-1] not in '。！？!?':
                reading += '。'
            assert words(reading) == words(raw), 'Reading copy changed transcript words'
            section['readingText'] = reading
            section['readingSource'] = 'ASR 分句整理，仅补标点；保留识别原词'
    return payload
