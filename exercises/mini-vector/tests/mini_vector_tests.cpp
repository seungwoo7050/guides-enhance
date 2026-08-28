#include "MiniVector.hpp"
#include "ThrowOnCopy.hpp"

#include <cassert>
#include <cstddef>
#include <stdexcept>

int ThrowOnCopy::live = 0;
int ThrowOnCopy::copiesBeforeThrow = -1;

static void normal_contract() {
    MiniVector<int> values;
    for (int i = 0; i < 20; ++i)
        values.push_back(i);
    assert(values.size() == 20 && values[19] == 19);

    MiniVector<int> copy(values);
    copy[0] = 99;
    assert(values[0] == 0);

    MiniVector<int> assigned;
    assigned = copy;
    assert(assigned[0] == 99);

    bool threw = false;
    try { values.at(20); }
    catch (const std::out_of_range &) { threw = true; }
    assert(threw);

    // 재할당 전에 기존 메모리를 지우는 구현은 aliasing[0]을 복사할 때 깨집니다.
    MiniVector<int> aliasing;
    aliasing.push_back(7);
    aliasing.push_back(aliasing[0]);
    assert(aliasing.size() == 2 && aliasing[0] == 7 && aliasing[1] == 7);
}

static void reserve_rollback() {
    MiniVector<ThrowOnCopy> values;
    values.push_back(ThrowOnCopy(1));
    values.push_back(ThrowOnCopy(2));
    const std::size_t oldSize = values.size();
    const std::size_t oldCapacity = values.capacity();
    const int liveBefore = ThrowOnCopy::live;

    // 일부 원소만 복사된 뒤 예외가 나도 원본과 live object 수가 유지되는지 확인합니다.
    ThrowOnCopy::copiesBeforeThrow = 1;
    try { values.reserve(oldCapacity + 10); assert(false); }
    catch (const std::runtime_error &) {}
    ThrowOnCopy::copiesBeforeThrow = -1;

    assert(values.size() == oldSize && values.capacity() == oldCapacity);
    assert(values[0].value == 1 && values[1].value == 2);
    assert(ThrowOnCopy::live == liveBefore);
}

static void push_back_rollback() {
    MiniVector<ThrowOnCopy> values;
    values.push_back(ThrowOnCopy(10));
    values.push_back(ThrowOnCopy(20));
    const std::size_t oldSize = values.size();
    const std::size_t oldCapacity = values.capacity();
    const int liveBefore = ThrowOnCopy::live;
    const ThrowOnCopy appended(30);

    // 기존 원소 복사는 성공하고 마지막 추가 복사만 실패하는 경우를 만듭니다.
    ThrowOnCopy::copiesBeforeThrow = 2;
    try { values.push_back(appended); assert(false); }
    catch (const std::runtime_error &) {}
    ThrowOnCopy::copiesBeforeThrow = -1;

    assert(values.size() == oldSize && values.capacity() == oldCapacity);
    assert(values[0].value == 10 && values[1].value == 20);
    assert(ThrowOnCopy::live == liveBefore + 1);
}

int main() {
    normal_contract();
    reserve_rollback();
    assert(ThrowOnCopy::live == 0);
    push_back_rollback();
    assert(ThrowOnCopy::live == 0);
}
