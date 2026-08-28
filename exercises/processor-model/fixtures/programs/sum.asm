# 5부터 1까지 더한 값을 메모리에 저장한 뒤 다시 읽습니다.
li r1, 5
li r2, 0
loop:
add r2, r2, r1
addi r1, r1, -1
bne r1, r0, loop
sw r2, 0(r0)
lw r3, 0(r0)
halt
