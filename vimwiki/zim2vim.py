#!/usr/bin/ipython3
# -*- coding: utf-8 -*-
"""
Converts ZimWiki to VimWiki.
Operates on an entire subdirectory of Zim zxt files.
Produces VimWiki in-place.
Operate on a copy or else!
Assume you have zim, task, vimwiki, and vimwiki-task plugins.
"""

# HTML stuff:
# sidebar issue suggestion: https://github.com/vimwiki/vimwiki/issues/805
# https://www.rosipov.com/blog/custom-templates-in-vimwiki/
# https://vi.stackexchange.com/questions/393/altering-html-templates-in-vimwiki
# https://github.com/coderiot/vimwiki-assets
# https://github.com/lotabout/vimwiki-tpl
# https://github.com/zweifisch/vimwiki-assets (highlight.js)
# https://github.com/rahul13ramesh/Dark-Vimwiki-Template
# https://wiki.thurstylark.com/Vimwiki.html (make git do the conversion?)
# The above one is great, though scripty!
# http://thedarnedestthing.com/vimwiki%20cheatsheet (another site template)
# default is in .vim/pack/foo/start/vimwiki/autoload/vimwiki
# TODO toc with no javascript? https://www.tipsandtricks-hq.com/simple-table-of-contents-toc-using-pure-html-and-css-code-9217
# https://www.w3schools.com/howto/howto_js_sidenav.asp
# TODO: bootstrap's documentation template layout 2 seems excellent, and even has search: https://themes.getbootstrap.com/product/guidebook-online-documentation-template/
# Just need the one page -- get that myself? Scrollspy on right, sidenav bar on left
# https://bootstrapious.com/p/bootstrap-sidebar
# https://materializecss.com/scrollspy.html
# http://www.codingeverything.com/2014/02/BootstrapDocsSideBar.html
# TODO: syntax highlight and background with css.
# TODO: mathjax line in html output
# TODO: nicer collapsing TOC with css/html? steal some from zim's?
# TODO: just build an expandable static tree of the whole thing and put it on left? auto-fold all but current
# TODO: auto top-of-page TOC with vimwiki - easy just put == Contents == at top
# TODO: Create my own source code include post-processing for html exports for website, so I don't need to keep source code in the wiki files themselves. A trial feature allows you to supply your own handler for wiki-include links.  See |VimwikiWikiIncludeHandler|.

# Vimwiki missing feature?
# TODO: what about renaming pages? Do links auto-rename? yes. But, not folders... even with g:vimwiki_dir_link
# TODO think about using the folder/index.wiki option instead of subfolder/subfolder.wiki?
# `:VimwikiRenameFile newpath/newname` can move a wiki page into different folders and updates links https://github.com/vimwiki/vimwiki/issues/926
# Still no way to rename a folder that is a parent of pages?

# Vimwiki bugs
# https://github.com/vimwiki/vimwiki/issues/354
# https://github.com/vimwiki/vimwiki/issues/581
# https://github.com/vimwiki/vimwiki/issues/997 (mine)

# Conversion itself
# TODO: before running on personal and work as whole, check for wiki files that
# aren't vimwiki, or other danger conditions? Run grep/find on all the
# conditions to check there are no innocent ones
# TODO: test taskwarrior stuff better

import os
import glob
import shutil
import re
from typing import List

# setup during debugging/development only
shutil.rmtree("index/")
# shutil.copytree("../Notebooks/Work/index/", "index")
# shutil.copyfile("../Notebooks/Work/index.zxt", "index.zxt")
shutil.copytree("../zim2vim/index/", "index")
shutil.copyfile("../zim2vim/index.zxt", "index.zxt")

# Grab all the zim files
filenames: List[str] = glob.glob("**/*.zxt", recursive=True)

for zxt in filenames:
    # Filenames
    folder = os.path.dirname(zxt)
    filename, extension = os.path.splitext(os.path.basename(zxt))
    newfile = (folder + "/" if folder else folder) + filename + ".wiki"
    shutil.move(zxt, newfile)

    # grab the file's data
    with open(newfile) as infile:
        content: str = infile.read()

    # Pre-process by replacing \t with 4 spaces
    content = re.sub("\t", "    ", content)

    # Stripping spaces at end of lines
    content = re.sub(" +\n", "\n", content)

    # un-done tasks
    content = content.replace("[ ] ", "* [ ] ")

    # canceled tasks - not a real equivalent in vimwiki
    content = content.replace("[x] ", "* [D] ")

    # done tasks
    content = content.replace("[*] ", "* [X] ")

    # Task dates -- TODO check on dates for taskwarrior
    # TODO: check
    # $ grep -E -r --include=\*.zxt *[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2} .
    # $ grep -E -r --include=\*.zxt \[*[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2} .
    # task type <isodate
    content = re.sub(r"(\* \[.?\].+)<[ ]*(\d{4}-\d{2}-\d{2})", r"\1(\2)", content)
    # task type [d: isodate]
    content = re.sub(r"(\* \[.?\].+)\[d\:[ ]*(\d{4}-\d{2}-\d{2})\]", r"\1(\2)", content)
    # single spaces inserted around ! inserted, or preserved
    content = re.sub(r"(\* \[.?\][^\!]+?)[ ]*(\!+)[ ]*(.*)", r"\1 \2 \3", content)

    # Task priority levels -- TODO check on priority for tw
    # TODO make more levels in TW, presevring number of ! from zim

    # Image sizing -- do image-width in css instead of here.
    # No beginning or end of line match because something could come after image
    # This was being greedy, ok now.
    content = re.sub("\?.+?}}", "}}", content)
    content = re.sub("\|image}}", "}}", content)

    # images directory more explicit and consistent with bash, in vim than zim
    content = content.replace("{{../", "{{local:")
    content = content.replace("{{./", "{{local:" + filename + "/")

    # attachment directory is the same as images above.
    # order matters with the below block and the next one:
    content = content.replace("[[../", "[[")
    content = content.replace("[[./", "[[" + filename + "/")

    # zim was [[subpage/subsubpage:subsubsubpage:subsubsubpage]],
    # fix to swap : for /
    # If python had PCRE: "(?:\G(?!\A)|\s*\()[^()\:]*\K\:", "#"
    # Ah, but this is so much more readable:
    # Makes sure this does not happen in code or verbatim blocks
    ingroup = False
    incodeblock = False
    lines = content.split("\n")
    relines = []
    for line in lines:
        if line.strip().startswith("{{{"):
            incodeblock = True
        elif line.strip().endswith("}}}"):
            incodeblock = False
        if "[[" and "]]" in line:
            chars = [line[0]]
            for ichar in range(1, len(line)):
                if line[ichar - 1 : ichar + 1] == "[[" and not incodeblock:
                    ingroup = True
                elif line[ichar - 1 : ichar + 1] == "]]":
                    ingroup = False
                if ingroup and line[ichar] == ":":
                    chars.append("/")
                else:
                    chars.append(line[ichar])
                ichar += 1
            line = "".join(chars)
        relines.append(line)
        ingroup = False
    lines = relines

    # Zim has too-relative ambiguous links to [[upinhierarchypages]] ...
    # This is ugly zim!
    # limit it to going past the index/current-dir
    # before processing [[./ [[../ and [[+ below, check validity of pageref
    # if pageref does not exist, search up, breadth-first
    # up single is done, but need to to up/down
    # TODO deal with matching down after finding folder
    # Phew, this was the hardest/nastiest to program in the whole conversion...
    relines = []
    for line in lines:
        linelinks = re.findall("\[\[\w[\/\w\-]{2,}\]\]", line)
        for linktext in linelinks:
            link = linktext[2:-2]
            if not os.path.isfile(link + "*.wiki") or not os.path.isfile(
                link + "*.zxt"
            ):
                up = folder
                dots = ""
                while True:
                    candidates = glob.glob((up + "/" if up else up) + "*.wiki")
                    candidates.extend(glob.glob((up + "/" if up else up) + "*.zxt"))
                    candidates = [
                        os.path.basename(os.path.splitext(candidate)[0])
                        for candidate in candidates
                    ]
                    if "/" in link:
                        split_link = link.split("/")
                        top = split_link[0]
                        down = "/" + "/".join(split_link[1:])
                    else:
                        top = link
                        down = ""
                    # print("folder was:", folder)
                    # print("filename was:", filename)
                    # print("searched dir up is:", up)
                    # print("broken link is:", link)
                    # print("top was:", top)
                    # print("down was:", down)
                    # print("were there multiple on one line?", len(linelinks))
                    # print("candidates are:", candidates, "\n")
                    if top in candidates:
                        line = line.replace(linktext, "[[" + dots + top + down + "]]")
                        # print("YAAAAAY", linktext, "replaced is:", line, "\n\n")
                        break
                    if not up:
                        break
                    up = os.path.dirname(up)
                    dots += "../"
        relines.append(line)
    content = "\n".join(relines)

    # change [[+subpage]] to the more sensibly explicit [[page/subpage]]
    content = content.replace("[[+", "[[" + filename + "/")

    # some of the zim [[ are pages links, and some are attachments
    # match [[../../whatever.py]] but not [[../../whatever]]
    # This could identify a file without an extension as a bad wiki page link,
    # but those are surely few, and could be fixed by hand.
    # Dealing with that would require processing zim headers...
    # TODO make sure no page names have . in them using grep/find
    # TODO maybe handle files these as source code inclusion?
    # content = re.sub(r"\[\[(.+[^/]\.[^/].+)\]\]", r"{{local:\1}}", content)
    content = re.sub(r"\[\[(.+?[^/]\.[^/].+?)\]\]", r"[[local:\1]]", content)

    # Table formatting
    content = content.replace("|:-", "|--")
    content = content.replace("-:|", "--|")
    content = content.replace("<|", "|")
    content = content.replace(">|", "|")
    content = content.replace("|<", "|")
    content = content.replace("|>", "|")

    # Headers are backwards from Zim
    # Manual swap needed to avoid progressive overwrite
    content = re.sub(r"====== (.+) ======\n", r"one \1 one\n", content)
    content = re.sub(r"===== (.+) =====\n", r"two \1 two\n", content)
    content = re.sub(r"==== (.+) ====\n", r"three \1 three\n", content)
    content = re.sub(r"=== (.+) ===\n", r"four \1 four\n", content)
    content = re.sub(r"== (.+) ==\n", r"five \1 five\n", content)

    content = re.sub(r"one (.+) one\n", r"= \1 =\n", content)
    content = re.sub(r"two (.+) two\n", r"== \1 ==\n", content)
    content = re.sub(r"three (.+) three\n", r"=== \1 ===\n", content)
    content = re.sub(r"four (.+) four\n", r"==== \1 ====\n", content)
    content = re.sub(r"five (.+) five\n", r"===== \1 =====\n", content)

    # Text formats
    # TODO some of these seem promiscuous, so
    # check them better with grep on raw notebook first

    # bold:
    content = re.sub(r"\*\*(.+?)\*\*", r"*\1*", content)

    # italic:
    content = re.sub(r"\/\/(.+?)\/\/", r"_\1_", content)

    # zim underline no equiv in vim, so go italic:
    content = re.sub(r"__(.+?)__", r"_\1_", content)

    # ''thing'' zim block for verbatim to `thing`:
    # ''i'' and ''j'' needs to be locally greedy
    # TODO what else needs greedy fixing like this did?
    # TODO search for .+ to see...
    # also in test file, I put things twice on one line, anything else?
    # It's only those where the start is the same as the finish (symmetrical)!
    # content = re.sub(r"''(.+)''", r"`\1`", content)
    content = re.sub(r"''(.+?)''", r"`\1`", content)

    # super-script:
    content = re.sub(r"_\{(.+?)\}", r",,\1,,", content)

    # sub-script:
    content = re.sub(r"\^\{(.+?)\}", r"^\1^", content)

    # horizontal lines should be ----
    # Mine
    content = content.replace(
        "\n__________________________________________________\n", "\n----\n"
    )
    # Zim's
    content = content.replace("\n--------------------\n", "\n----\n")

    # line-by-line operations start here:
    lines = content.split("\n")

    # Delete zim headers
    lines: List[str] = [
        line + "\n"
        for line in lines
        if not (
            line.startswith("Content-Type: text/x-zim-wiki")
            or line.startswith("Wiki-Format: zim")
            or line.startswith("Creation-Date:")
        )
    ]

    # Delete blank line left at top
    if lines[0] == "\n":
        lines = lines[1:]

    # latex to in-page mathjax!
    # All of the in-page equations should be named with equation.tex/png
    # All my equations should be single-line? - yes in website at least
    # TODO archive the comment of old tex file in-page somehow?
    # Just validate instead.
    # Do a grep/find before running this on the whole notebook.
    # TODO double-check this one
    relines = []
    for line in lines:
        eqnames = re.findall("{{local:.+?\/(equation.+?)\}\}", line)
        replacenames = re.findall("{{local:.+?\/equation.+?\}\}", line)
        if eqnames:
            for eq, replaceme in zip(eqnames, replacenames):
                eqname = eq.split(".")[0]
                with open(
                    (folder + "/" if folder else folder)
                    + filename
                    + "/"
                    + eqname
                    + ".tex"
                ) as filein:
                    equation = filein.read()
                line = line.replace(replaceme, "$ " + equation + " $")
            relines.append(line)
        else:
            relines.append(line)
    lines = relines

    # Update code blocks for auto-vim highlighting
    # TODO Post-process these in css/html export?
    lines = [
        "{{{python\n" if line.startswith('{{{code: lang="python"') else line
        for line in lines
    ]
    lines = [
        "{{{bash\n" if line.startswith('{{{code: lang="sh"') else line for line in lines
    ]
    lines = [
        "{{{cpp\n" if line.startswith('{{{code: lang="cpp"') else line for line in lines
    ]
    lines = [
        "{{{c\n" if line.startswith('{{{code: lang="c"') else line for line in lines
    ]

    # Clean up newlines for spacing.
    # no newlines between {{{ }}} or ''' '''
    # ''' ''' zim blocks (which got converted to {{{ }}})
    # except in Python code in page, so don't do there
    # TODO 4-space block quotes? check how they look with no space
    incodeblock = False
    inlitblock = False
    relines = []
    for line in lines:
        if line.strip().startswith("{{{"):
            incodeblock = True
        elif line.strip().endswith("}}}"):
            incodeblock = False
        if incodeblock:
            relines.append(line)
        else:
            if line.strip().endswith("'''") and inlitblock:
                inlitblock = False
                line = line.replace("'''", "}}}")
            if line.strip().startswith("'''"):
                inlitblock = True
                line = line.replace("'''", "{{{")
            if (
                inlitblock
                or line.strip().startswith("* ")
                or line.strip().startswith("=")
                or line == "----\n"
                or line.strip().startswith("|-")
                or line.strip().startswith("| ")
                or re.search("^[0-9]+\. ", line.strip())
                or re.search("^[0-9]+\) ", line.strip())
                or re.search("^[a-zA-Z]{1}\. ", line.strip())
                or re.search("^[a-zA-Z]{1}\) ", line.strip())
            ):
                relines.append(line)
            else:
                relines.append(line + "\n")
    # re-join for further processing
    content = "".join(relines)
    # Replace 3+ consecutive newlines with 2, to clean up compactness
    content = re.sub("\n{3,}", "\n\n", content)

    # Write it all out to the file
    with open(newfile, "w") as outfile:
        outfile.write(content)
