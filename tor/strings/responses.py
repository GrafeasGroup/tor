import tor.strings.translation

db = tor.strings.translation(lang='en_US')


thumbs_up_gifs = db['urls']['thumbs_up_gifs']

bot_footer = db['responses']['bot_footer'].strip()
claim_success = db['responses']['claim']['success'].strip()
already_claimed = db['responses']['claim']['already_claimed'].strip()
claim_already_complete = db['responses']['claim']['already_complete'].strip()
done_still_unclaimed = db['responses']['done']['still_unclaimed'].strip()
done_completed_transcript = db['responses']['done']['completed_transcript'].strip()
done_cannot_find_transcript = db['responses']['done']['cannot_find_transcript'].strip()
unclaim_still_unclaimed = db['responses']['unclaim']['still_unclaimed'].strip()
unclaim_success = db['responses']['unclaim']['success'].strip()
unclaim_success_with_report = db['responses']['unclaim']['success_with_report'].strip()
unclaim_success_without_report = db['responses']['unclaim']['success_without_report'].strip()
unclaim_failure_post_already_completed = db['responses']['unclaim']['post_already_completed'].strip()
something_went_wrong = db['responses']['general']['oops'].strip()
please_accept_coc = db['responses']['general']['coc_not_accepted'].strip()
youre_welcome = db['responses']['general']['youre_welcome'].strip()
pm_subject = db['responses']['direct_message']['subject'].strip()
pm_body = db['responses']['direct_message']['body'].strip()
transcript_on_tor_post = db['responses']['general']['transcript_on_tor_post'].strip()
