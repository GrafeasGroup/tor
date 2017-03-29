from praw import Reddit

r = Reddit('bot')

ToS = 'TranscribersOfReddit'

domains = r.subreddit(ToS).wiki['domains'].content_md
domains = ''.join(domains.splitlines()).split('---')

video_domains, audio_domains, image_domains = [], [], []

for domainset in domains:
    domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
    current_domain_list = []
    if 'video' in domainset:
        current_domain_list = video_domains
    elif 'audio' in domainset:
        current_domain_list = audio_domains
    elif 'images' in domainset:
        current_domain_list = image_domains
    [current_domain_list.append(x) for x in domain_list]

