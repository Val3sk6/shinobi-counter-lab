#!/usr/bin/env python3
"""Manual/authorized evidence intake: preview candidates, then human-approved promotion.

No network calls, cookies, logins or scraping. Requires original evidence already
collected by the contributor with appropriate authorization.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HERO_FILE = ROOT / 'data/heroes.json'
CASE_FILE = ROOT / 'data/cases.json'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def names_index(heroes):
    known = heroes['heroes']
    aliases = heroes['aliases']
    names = {name: name for name in known}
    names.update(aliases)
    return names


def extract_names(text, index):
    """Greedy non-overlapping entity recognition; never guess an unknown nickname."""
    text = text or ''
    matches = []
    keys = sorted(index, key=lambda x: (-len(x), x))
    regex = re.compile('|'.join(re.escape(k) for k in keys))
    for match in regex.finditer(text):
        matches.append(index[match.group()])
    return matches


def extract_team(text, index):
    found = extract_names(text, index)
    return found if len(found) == 3 and len(set(found)) == 3 else None


def role_sections(text):
    """Only explicitly labelled descriptions qualify for paired auto-extraction."""
    enemy = re.search(r'(?:防守|敌方|对面|守方)\s*[:：]\s*(.+?)(?=\s*(?:进攻|我方|破阵|破解|攻方)\s*[:：]|$)', text, re.S)
    attack = re.search(r'(?:进攻|我方|破阵|破解|攻方)\s*[:：]\s*(.+?)(?=\s*(?:防守|敌方|对面|守方)\s*[:：]|$)', text, re.S)
    return (enemy.group(1) if enemy else None, attack.group(1) if attack else None)


def span_note(text):
    # Mention, not independently verified threshold. Unclear denominator stays unspecified.
    match = re.search(r'(?:跨(?:度|战力)?|跨度(?:约|为|在)?|跨战力)\s*(?:约|达|到|了|为|≈|:|：|≤|小于|不超过|以下)?\s*(\d+(?:\.\d+)?)\s*%', text or '')
    return '来源文字提及 ' + match.group(1) + '%（含义及分母待核）' if match else '未提供'


def generate_id(url, channel, *comment_ids):
    key = '|'.join([url, channel, *[str(x) for x in comment_ids]])
    return 'biliv-' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:14]


def safe_url(url):
    p = urlparse(url)
    if p.scheme not in ('https', 'http') or not p.netloc:
        raise ValueError('video_url must be an http(s) link')
    return url


def candidate(src, channel, defensive, offensive, index, root_id='', reply_id='', supporting_text='', author_confirmed=False, reply_published_at=''):
    url = safe_url(src['video_url'])
    published = (reply_published_at if channel == 'comment' else src.get('published_at', ''))
    date_known = bool(re.fullmatch(r'20\d\d-\d\d-\d\d', published))
    if channel == 'description' and not date_known:
        raise ValueError('published_at must be YYYY-MM-DD (do not infer publication date)')
    defenders = extract_team(defensive, index)
    attackers = extract_team(offensive, index)
    complete = defenders is not None and attackers is not None
    if not complete:
        reason = '未能唯一识别双方各三个忍者；需人工补全'
    elif channel == 'comment' and not author_confirmed:
        reason = '不是视频作者的回复，只能当作玩家线索'
    elif not date_known:
        reason = '缺少评论回复的准确日期，必须核实后才能入库'
    else:
        reason = '阵容文字完整，但仍需人工核对原始来源和适用条件'
    source_ref = {'platform': src.get('platform', 'bilibili'), 'videoUrl': url,
                  'videoId': src.get('video_id', ''), 'channel': channel}
    if channel == 'comment':
        source_ref.update({'rootCommentId': str(root_id), 'replyId': str(reply_id),
                           'replyIsVideoAuthor': bool(author_confirmed)})
    cid = generate_id(url, channel, root_id, reply_id)
    case = None
    if complete:
        case = {
            'id': cid,
            'title': ' · '.join(defenders) + ' → ' + ' · '.join(attackers),
            'def': defenders, 'atk': attackers,
            'note': '依据人工整理的标题简介或评论问答；未证明必胜或跨战力能力。',
            'lim': span_note(supporting_text),
            'evidence': '标题/简介摘录' if channel == 'description' else '玩家提问与视频作者回复',
            'grade': 'primary', 'date': published if date_known else '', 'url': url,
            'source': 'B站标题与简介（人工收集）' if channel == 'description' else 'B站作者回复（人工收集）',
            'condition': '待人工复核（含站位及技能细节）',
            'version': '',  # Must be set by a reviewer; publication month != game patch.
            'review': 'hold', 'validation': '程序候选；尚未经人工复核',
            'spanBasis': 'unspecified', 'mode': '积分赛',
            'sourceRef': source_ref,
        }
    return {'candidateId': cid, 'channel': channel, 'sourceRef': source_ref,
            'enemyText': defensive, 'attackText': offensive,
            'detectedDefense': defenders, 'detectedAttack': attackers,
            'readyForReview': bool(complete and date_known and (channel != 'comment' or author_confirmed)),
            'reason': reason, 'case': case}


def preview(source_path, output_path):
    src = read_json(source_path)
    names = names_index(read_json(HERO_FILE))
    if not isinstance(src.get('comments', []), list):
        raise ValueError('comments must be an array')
    found = []
    title = src.get('title', '')
    desc = src.get('description', '')
    left, right = role_sections(title + '\n' + desc)
    if left is not None or right is not None:
        found.append(candidate(src, 'description', left or '', right or '', names, supporting_text=title+'\n'+desc))
    owner_id = str(src.get('video_owner_id') or '')
    for comment in src.get('comments', []):
        question = comment.get('text', '')
        replies = comment.get('replies', [])
        if not isinstance(replies, list):
            raise ValueError('replies must be an array')
        # Each question and its reply must stay together; community replies get lower trust.
        for reply in replies:
            reply_text = reply.get('text', '')
            is_owner = bool(owner_id and str(reply.get('author_id', '')) == owner_id)
            # Skip casual community chat without two complete three-ninja lineups.
            if not is_owner and not (extract_team(question, names) and extract_team(reply_text, names)):
                continue
            found.append(candidate(src, 'comment', question, reply_text, names,
                root_id=comment.get('comment_id', ''), reply_id=reply.get('reply_id', ''),
                supporting_text=question+'\n'+reply_text, author_confirmed=is_owner,
                reply_published_at=reply.get('published_at','')))
    seen = set()
    distinct = []
    for entry in found:
        if entry['candidateId'] not in seen:
            seen.add(entry['candidateId'])
            distinct.append(entry)
    write_json(output_path, {'schema': 'shinobi-proposals-v1', 'sourceFile': Path(source_path).name,
                             'candidates': distinct})
    print(f'Extracted {len(distinct)} candidates; {sum(x["readyForReview"] for x in distinct)} parsable. Saved: {output_path}')


def approve(proposals_path, candidate_id, version, confirmed=False):
    if not confirmed:
        raise ValueError('Human reviewer must pass --confirmed after checking original source')
    if not re.fullmatch(r'20\d\d-\d\d', version):
        raise ValueError('version must be confirmed YYYY-MM (not inferred from upload date)')
    doc = read_json(proposals_path)
    found = [c for c in doc['candidates'] if c['candidateId'] == candidate_id]
    if len(found) != 1 or not found[0]['readyForReview'] or not found[0]['case']:
        raise ValueError('Not a complete/author-confirmed proposal; review it manually')
    case = found[0]['case'].copy()
    case['version'] = version
    case['review'] = 'ready'
    case['condition'] = '作者文本给出的三站位；其他适用条件仍以来源为准'
    case['validation'] = '人工确认原始阵容文字；实战效果未独立复测'
    raw = read_json(CASE_FILE)
    if any(c['id'] == case['id'] for c in raw['cases']):
        raise ValueError('Already imported; no duplicate insert')
    if any(c['def'] == case['def'] and c['atk'] == case['atk'] and c['version'] == version for c in raw['cases']):
        raise ValueError('Same matchup in the same version already exists; consolidate sources manually')
    raw['cases'].append(case)
    write_json(CASE_FILE, raw)
    print('Approved', candidate_id, '-> data/cases.json; now run python scripts/build.py')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command', required=True)
    scan = subs.add_parser('preview', help='Extract candidates from human-supplied evidence JSON')
    scan.add_argument('source')
    scan.add_argument('--out', default='build/proposals.json')
    promote = subs.add_parser('approve', help='Promote one MANUALLY VERIFIED candidate')
    promote.add_argument('proposals')
    promote.add_argument('--id', required=True)
    promote.add_argument('--version', required=True, help='Confirmed game version YYYY-MM')
    promote.add_argument('--confirmed', action='store_true', help='I checked the source, three slots and patch version')
    args = p.parse_args()
    if args.command == 'preview':
        preview(args.source, args.out)
    else:
        approve(args.proposals, args.id, args.version, confirmed=args.confirmed)


if __name__ == '__main__':
    main()