identification division.
program-id. eb-roundtrip.
environment division.
input-output section.
file-control.
    select input-file assign to "input.dat"
        organization is sequential file status is input-status.
    select output-file assign to "output.dat"
        organization is sequential file status is output-status.
data division.
file section.
fd input-file recording mode is F record contains 16460 characters.
copy "envelope.cpy".
fd output-file recording mode is F record contains 16460 characters.
01 output-record pic X(16460).
working-storage section.
01 input-status pic XX.
01 output-status pic XX.
procedure division.
    open input input-file
    if input-status not = "00"
        display "OPEN INPUT: " input-status
        move 1 to return-code stop run
    end-if
    open output output-file
    if output-status not = "00"
        display "OPEN OUTPUT: " output-status
        move 1 to return-code stop run
    end-if
    perform until input-status = "10"
        read input-file
        evaluate input-status
            when "00"
                move EB-RECORD to output-record
                write output-record
                if output-status not = "00"
                    display "WRITE: " output-status
                    move 1 to return-code stop run
                end-if
            when "10" continue
            when other
                display "READ: " input-status
                move 1 to return-code stop run
        end-evaluate
    end-perform
    close input-file output-file
    if input-status not = "00" or output-status not = "00"
        display "CLOSE: " input-status " " output-status
        move 1 to return-code stop run
    end-if
    move 0 to return-code
    stop run.
