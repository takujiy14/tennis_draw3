import streamlit as st
import random
import itertools

# ページの設定
st.set_page_config(page_title="テニス抽選アプリ", page_icon="🎾", layout="centered")

st.title("🎾 テニス抽選")
st.write("created by t.yoshida")
st.write("子のアプリは予告なく終了する場合があります。")

# --- 1. 入力エリア ---
col1, col2 = st.columns(2)
with col1:
    num_p = st.number_input("人数（人）", min_value=4, value=6, step=1)
with col2:
    num_c = st.number_input("コート面数（面）", min_value=1, value=1, step=1)

# エラーチェック
if num_p < (num_c * 4):
    st.error(f"⚠️ {num_c}面には最低{num_c*4}人必要です。人数を増やすか、面数を減らしてください。")
    st.stop()

# --- 2. 抽選ロジック ---
if st.button("✨ 抽選する", type="primary"):
    
    # プレイヤーの初期化
    players = []
    for i in range(1, num_p + 1):
        players.append({
            'id': i,
            'count': 0,
            'partners': {j: 0 for j in range(1, num_p + 1) if i != j},
            'opponents': {j: 0 for j in range(1, num_p + 1) if i != j},
            'last_played': -1 
        })

    # ペア(小, 大)ごとの「最後に一緒に組んだ試合番号」を記録する辞書
    pair_last_match = {}

    match_list = []
    match_no = 1
    set_no = 1
    next_serial_id = 1  # 1巡目連番用
    
    while match_no <= 20:
        current_set_matches = []
        set_selected_ids = []  # この回戦で選出済みの人
        
        for c in range(1, num_c + 1):
            if match_no > 20: break
            
            selected_ids = []
            
            # --- A. 1巡目の完全連番フェーズ（アプリ起動直後の初期出し） ---
            if next_serial_id <= num_p:
                for _ in range(4):
                    if next_serial_id <= num_p:
                        selected_ids.append(next_serial_id)
                        next_serial_id += 1
                
                # 端数補充が必要な場合
                if len(selected_ids) < 4:
                    needed = 4 - len(selected_ids)
                    
                    def get_initial_fallback_score(player):
                        if player['id'] in selected_ids or player['id'] in set_selected_ids:
                            return 999999
                        return (player['count'] * 100000) - (set_no - player['last_played']) * 100 + random.random()
                    
                    pool = [p for p in players]
                    pool.sort(key=get_initial_fallback_score)
                    for _ in range(needed):
                        if pool and get_initial_fallback_score(pool[0]) < 999999:
                            selected_ids.append(pool.pop(0)['id'])
                            
                # 4人を確定
                p_ids = selected_ids
            
            # --- B. 2巡目以降：【新方式】コンビ総当たりスコアリングフェーズ ---
            else:
                # まだこの回戦に選ばれていない、かつ全プレイヤーから選べる4人の組み合わせをすべて列挙
                available_players = [p for p in players if p['id'] not in set_selected_ids]
                if len(available_players) < 4:
                    # 万が一足りない場合は全体から（基本的には num_p >= 4面数 なのでここはセーフ）
                    available_players = players
                
                best_combination = None
                best_score = float('inf')
                
                # 選べる人の中から「4人」を選ぶ全パターンを検証
                for combo in itertools.combinations([p['id'] for p in available_players], 4):
                    # 4人の中でさらに「ペア2組」を作る3パターンを検証
                    # パターン1: (a,b) vs (c,d)
                    # パターン2: (a,c) vs (b,d)
                    # パターン3: (a,d) vs (b,c)
                    a, b, c, d = combo
                    possible_pairings = [
                        ((a, b), (c, d)),
                        ((a, c), (b, d)),
                        ((a, d), (b, c))
                    ]
                    
                    for pair1, pair2 in possible_pairings:
                        # 常に小・大の順に並び替え
                        key1 = (min(pair1), max(pair1))
                        key2 = (min(pair2), max(pair2))
                        
                        # ★【最重要】直近2試合以内に組んだペアが1組でも含まれていたら、その組み合わせの点数を絶望的に悪くする
                        interval_penalty = 0
                        if match_no - pair_last_match.get(key1, -999) <= 2:
                            interval_penalty += 5000000
                        if match_no - pair_last_match.get(key2, -999) <= 2:
                            interval_penalty += 5000000
                        
                        # その他の基本スコア計算（試合数の平準化など）
                        comb_players = [next(p for p in players if p['id'] == pid) for pid in [a, b, c, d]]
                        counts_score = sum(p['count'] * 100000 for p in comb_players)
                        rest_score = -sum((set_no - p['last_played']) * 10000 for p in comb_players)
                        
                        # 過去の対戦・ペア重複ペナルティ
                        history_penalty = 0
                        p_objs = {pid: next(p for p in players if p['id'] == pid) for pid in [a,b,c,d]}
                        # pair1
                        history_penalty += p_objs[pair1[0]]['partners'].get(pair1[1], 0) * 50
                        # pair2
                        history_penalty += p_objs[pair2[0]]['partners'].get(pair2[1], 0) * 50
                        # 対戦
                        for team1_p in pair1:
                            for team2_p in pair2:
                                history_penalty += p_objs[team1_p]['opponents'].get(team2_p, 0) * 10
                        
                        total_score = interval_penalty + counts_score + rest_score + history_penalty + random.random()
                        
                        if total_score < best_score:
                            best_score = total_score
                            best_combination = (pair1, pair2)
                
                # 最もスコアが良い（＝直近2試合で被っておらず、試合数も公平な）4人＆ペアを採用
                p_ids = [best_combination[0][0], best_combination[0][1], best_combination[1][0], best_combination[1][1]]
            
            # --- C. データの更新と保存 ---
            p1 = next(p for p in players if p['id'] == p_ids[0])
            p2 = next(p for p in players if p['id'] == p_ids[1])
            p3 = next(p for p in players if p['id'] == p_ids[2])
            p4 = next(p for p in players if p['id'] == p_ids[3])

            set_selected_ids.extend([p1['id'], p2['id'], p3['id'], p4['id']])

            # ペアの結成履歴を(小, 大)で保存
            pair1_key = (min(p1['id'], p2['id']), max(p1['id'], p2['id']))
            pair2_key = (min(p3['id'], p4['id']), max(p3['id'], p4['id']))
            pair_last_match[pair1_key] = match_no
            pair_last_match[pair2_key] = match_no

            # 個人スタッツ更新
            for p in [p1, p2, p3, p4]:
                p['count'] += 1
                p['last_played'] = set_no
                
            p1['partners'][p2['id']] += 1; p2['partners'][p1['id']] += 1
            p3['partners'][p4['id']] += 1; p4['partners'][p3['id']] += 1
            for opp in [p3, p4]:
                p1['opponents'][opp['id']] += 1; opp['opponents'][p1['id']] += 1
                p2['opponents'][opp['id']] += 1; opp['opponents'][p2['id']] += 1

            current_set_matches.append({
                'no': match_no, 'court': c,
                'p1': (p1['id'], p2['id']), 'p2': (p3['id'], p4['id'])
            })
            match_no += 1
        
        match_list.append({'set_no': set_no, 'matches': current_set_matches})
        set_no += 1

    # --- 3. 表示処理 ---
    # st.success("🎉 試合数均等 ＆ 実質同一ペアの連続を完全に根絶した乱数表が完成しました！")
    
    for s in match_list:
        if not s['matches']: continue
        st.markdown(f"### 🗓️ 【第 {s['set_no']} 回戦】")
        
        for m in s['matches']:
            st.info(f"**コート {m['court']}** (第 {m['no']:02} 試合)  👉  **{m['p1'][0]} - {m['p1'][1]}** vs  **{m['p2'][0]} - {m['p2'][1]}**")
    
    st.divider()
    st.markdown("### 📊 【個人集計】")
    players.sort(key=lambda x: x['id'])
    
    cols_stats = st.columns(4)
    for idx, p in enumerate(players):
        with cols_stats[idx % 4]:
            st.metric(label=f"選手 {p['id']}", value=f"{p['count']} 回")