import sublime
import re

ST_EM = 0 # empty
ST_SS = 11 # step start
ST_SE = 12 # step end
ST_MS = 21 # macro start
ST_ME = 22 # macro end
ST_MF = 23 # macro function
ST_OS = 31 # ods (rtf/excel/html) start
ST_OE = 32 # ods (rtf/excel/html) end
ST_OP = 4 # ods/options/
ST_OT = 6 # other
ST_QT = -1 # quoted
ST_CT = -2 # comment

class BlockGetter:
	def __init__(self):
		self.view = sublime.active_window().active_view()
	def extract_sentence(self, pt, include_newline=True, include_blank=True):
	    """ get the sentence location from cursor location""" 
	    cview = self.view
	    # print(pt)
	    if re.search("comment",cview.scope_name(pt)):
	        return cview.extract_scope(pt)
	    else:
	        pt_pre_nb = pt_pre = pt_post = pt_mark = pt
	        while pt_pre > 0:
	            singlestr = cview.substr(sublime.Region(pt_pre-1,pt_pre))
	            if singlestr == ";":
	                if not re.search("(quoted)", cview.scope_name(pt_pre)):
	                    break
	            elif re.search("comment", cview.scope_name(pt_pre-1)):
	                pt_pre += 1 
	                break
	            pt_pre -=  1
	            # if string is a blank and we set the parameter to not update the location at the blank
	            # then we will not update pt_mark
	            if len(singlestr.strip()) == 0:
	                if include_blank:
	                    if re.search("\n",singlestr):
	                        if include_newline:
	                            pt_mark = pt_pre
	                    else:
	                        pt_mark = pt_pre
	                else:
	                    pass
	            else:
	                # update pt_mark
	                pt_mark = pt_pre
	                
	        pt_pre_nb = pt_mark
	        scp_is_comment = False
	        scp_is_comment_pre = False
	        while pt_post < cview.size():
	            singlestr = cview.substr(sublime.Region(pt_post,pt_post+1))
	            scpn = cview.scope_name(pt_post)
	            if re.search("comment", scpn):
	                scp_is_comment = True
	            else:
	                scp_is_comment = False
	            if singlestr == ";":
	                if not re.search("(quoted)", scpn):
	                    pt_post += 1
	                    break
	            elif (not scp_is_comment) & scp_is_comment_pre:
	                break
	            scp_is_comment_pre = scp_is_comment
	            pt_post += 1
	        return sublime.Region(pt_pre_nb, pt_post)

	def get_sen_info(self, pt, include_newline=True,include_blank=True):
	    cview = self.view
	    sen = self.extract_sentence(pt,include_newline=include_newline,include_blank=include_blank)
	    senstr = cview.substr(sen)
	    if len(senstr.strip()) <= 1:
	        sen_type = ST_EM
	        return {"sen_begin":sen.begin(), "sen_end":sen.end(), "sen_type":sen_type}
	    # scn: scope name
	    scn = cview.scope_name(sen.begin()+re.search(r"\S",senstr).start())

	    if re.search("quoted",scn):
	        sen_type = ST_QT
	    elif re.search("comment",scn):
	        sen_type = ST_CT
	    elif re.sub(r"\s", "", senstr) in ("run;","quit;"):
	        sen_type = ST_SE
	    else:
	        keyword_r = re.search(r"\S+\b", senstr)
	        if keyword_r is None:
	            keyword = ""
	        else:
	            keyword = keyword_r.group(0).lower()
	        if keyword in ("proc","data"):
	            sen_type = ST_SS
	        elif keyword == "%macro":
	            sen_type = ST_MS
	        elif keyword == "%mend":
	            sen_type = ST_ME
	        elif re.search("%", keyword):
	            sen_type = ST_MF
	        elif re.search(r"^\s*ods\s+(rtf|excel|html)\s+(file)",senstr.lower()):
	            sen_type = ST_OS
	        elif re.search(r"^\s*ods\s+(rtf|excel|html)\s+(close)",senstr.lower()):
	            sen_type = ST_OE
	        elif keyword in ("ods","options","dm","title","foodnote","libname","filename", "x") or re.search(r"(title)|(footnote)\d*$", keyword):
	            sen_type = ST_OP
	        else:
	            sen_type = ST_OT
	    return {"sen_begin":sen.begin(), "sen_end":sen.end(), "sen_type":sen_type}

	def expand_macro_define(self, pt):
	    cview = self.view
	    sen = self.extract_sentence(pt,include_newline=False)
	    sel_begin = min(sen.begin(), pt)
	    senstr = cview.substr(sen).lower()
	    mn = re.search(r"(?<=%macro)\s+\S+\w\s*(?=\(|;)", senstr).group(0).strip()
	    ml = 1 # level of macro
	    pt_pre = pt_cur = sen.end() - 1
	    while True:
	        sen_info = self.get_sen_info(pt_cur)
	        sen_type=sen_info['sen_type']
	        if sen_type == ST_MS:
	            if pt_cur == pt_pre:
	                pass
	            else:
	                ml += 1
	        elif sen_type == ST_ME:
	            mn_end_rs = re.search(r"(?<=%mend)\s+\S+\w\s*(?=\(|;)", senstr)
	            if mn_end_rs:
	                mn_end = mn_end_rs.group(0).strip()
	                if mn_end is mn:
	                    ml = 0
	                else:
	                    ml -= 1
	            else:
	                ml -= 1
	        
	        if ml == 0:
	            sel_end = sen_info['sen_end']
	            break
	        if pt_cur >= cview.size():
	            sel_end = pt_pre
	            break
	        pt_pre = sen_info['sen_end']
	        pt_cur = pt_pre+1
	    return sublime.Region(sel_begin, sel_end)

	# move the cursor backwards to the begining of a step
	def expand_scope(self,pt):
	    cview=self.view
	    sen = self.extract_sentence(pt)
	    sel_begin = min(sen.begin(),pt) # sel_begin: selection begining
	    sel_end = max(sen.end(),pt)     # sel_end: selection ending
	    # set the current point at the begining of this sentence
	    pt_pre = pt_cur = sen.begin()   # pt_cur: current point location; pt_pre: previous point location
	    n_lines_processed = 0
	    while True:
	        sen_info = self.get_sen_info(pt_cur)
	        sen_type=sen_info['sen_type']
	        if sen_type in (ST_SS, ST_MS, ST_OS):
	            if n_lines_processed == 0:
	                # print("Stop at first line")
	                sel_begin = self.get_sen_info(pt,include_newline=False,include_blank=True)['sen_begin']
	            elif sen_type in (ST_SS, ST_OS):
	                # print("Stop at ss and os")
	                sel_begin = self.get_sen_info(pt_cur,include_newline=False,include_blank=True)['sen_begin']
	            else:
	                # print("Stop at others")
	                # print(pt_pre)
	                sel_begin = self.get_sen_info(pt_pre,include_newline=False,include_blank=False)['sen_begin']
	            break
	        else:
	            pass
	        # save the location of last end
	        pt_pre = sen_info['sen_begin']
	        # move to the next end
	        pt_cur = pt_pre - 1
	        if pt_cur < 0:
	            sel_begin = 0
	            break
	        # if move backwards to the last step/macro:
	        elif self.get_sen_info(pt_cur)['sen_type'] in (ST_SE, ST_ME):
	            sel_begin = self.get_sen_info(pt_pre,include_newline=False,include_blank=False)['sen_begin']
	            break
	        n_lines_processed += 1

	    # Now move the cursor forward
	    pt_pre = pt_cur = sen.end()-1
	    is_rtf_scope = True if self.get_sen_info(pt)['sen_type'] == ST_OS else False
	    while True:
	        sen_info = self.get_sen_info(pt_cur)
	        sen_type=sen_info['sen_type']
	        # if it is the first time encounter SS and MS then continue
	        # otherwise stop the loop
	        if sen_type in (ST_SS, ST_MS, ST_OS):
	            if pt_cur == pt_pre:
	                pass
	            else:
	                if is_rtf_scope:
	                    pass
	                else:
	                    # use last end as the sel_end
	                    sel_end = pt_pre
	                    break
	        elif sen_type == ST_SE:
	            if is_rtf_scope:
	                pass
	            else:
	                # use the current end as the sel_end
	                sel_end = sen_info['sen_end']
	                break
	        elif sen_type == ST_OE:
	            if is_rtf_scope:
	                sel_end = sen_info['sen_end']
	                break
	            else:
	                sel_end = self.get_sen_info(pt_pre)['sen_end']
	                break
	        else:
	            pass
	        # save the location of last end
	        pt_pre = sen_info['sen_end']
	        # move to the next begin
	        pt_cur = pt_pre + 1
	        if pt_cur >= cview.size():
	            sel_end = pt_pre
	            break
	    return sublime.Region(sel_begin, sel_end)

	def expand_comment(self,pt):
	    cview=self.view
	    sen = self.extract_sentence(pt)
	    sel_begin = min(sen.begin(),pt) # sel_begin: selection begining
	    sel_end = max(sen.end(),pt)     # sel_end: selection ending
	    # set the current point at the begining of this sentence
	    pt_pre = pt_cur = sen.begin()   # pt_cur: current point location; pt_pre: previous point location
	    n_lines_processed = 0
	    while True:
	        sen_info = self.get_sen_info(pt_cur)
	        sen_type=sen_info['sen_type']
	        if sen_type != ST_CT:
	            sel_begin = self.get_sen_info(pt_pre,include_newline=False,include_blank=True)['sen_begin']
	            break
	        else:
	            pass
	        # save the location of last end
	        pt_pre = sen_info['sen_begin']
	        # move to the next end
	        pt_cur = pt_pre - 1
	        if pt_cur < 0:
	            sel_begin = 0
	            break
	        n_lines_processed += 1

	    # Now move the cursor forward
	    pt_pre = pt_cur = sen.end()-1
	    while True:
	        sen_info = self.get_sen_info(pt_cur)
	        sen_type=sen_info['sen_type']
	        if sen_type != ST_CT:
	            sel_end = self.get_sen_info(pt_pre)['sen_end']
	            break
	        else:
	            pass
	        # save the location of last end
	        pt_pre = sen_info['sen_end'] - 1
	        # move to the next begin
	        pt_cur = pt_pre + 1
	        if pt_cur >= cview.size():
	            sel_end = sen_info['sen_end']
	            break
	    return sublime.Region(sel_begin, sel_end)

	def expand_region_selection(self, sel):
	    cview=self.view
	    pt = sel.begin()
	    sen_info = self.get_sen_info(pt)
	    sen_type = sen_info['sen_type']
	    # print("Sentence type is %s" % sen_type)
	    if sen_type == ST_MS:
	        # print("Expanding macro")
	        sel_region = self.expand_macro_define(pt)
	    elif sen_type in (ST_MF, ST_OP):
	        # print("Expanding macro function")
	        sen_info_updated = self.get_sen_info(pt,include_newline=False,include_blank=True)
	        sel_region = sublime.Region(sen_info_updated['sen_begin'],sen_info_updated['sen_end'])
	    elif sen_type == ST_CT:
	        sel_region = self.expand_comment(pt)
	    else:
	        # print("Expanding others") 
	        sel_region = self.expand_scope(pt)
	    self.view.sel().add(sel_region)
	    return cview.substr(sel_region)
