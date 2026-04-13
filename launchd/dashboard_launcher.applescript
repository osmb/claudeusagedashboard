on run
    -- Start service if not already running
    set svcCheck to do shell script "launchctl list | grep com.osmb.ccusage || true"
    if svcCheck does not contain "com.osmb.ccusage" then
        do shell script "launchctl start com.osmb.ccusage"
        delay 2
    end if
    -- Open dashboard in default browser
    open location "http://localhost:8501"
end run
