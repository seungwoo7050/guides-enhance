#include "Store.hpp"
#include "Errors.hpp"

#include <stdexcept>
#include <utility>

Store::Store(std::size_t capacity)
    : capacity_(capacity), data_() {
    if (capacity_ == 0)
        throw std::invalid_argument("store capacity must be greater than zero");
}

// [Implementation 3-1] Validate before inserting
// 중복과 용량을 확인하고 값 복사를 끝낸 뒤 map을 변경합니다.
void Store::putNew(const std::string &key, const std::string &value) {
    if (data_.find(key) != data_.end())
        throw ConflictError("key already exists");
    if (data_.size() >= capacity_)
        throw StoreFullError("store capacity reached");

    const TextBuffer ownedValue(value.c_str());
    const std::pair<std::map<std::string, TextBuffer>::iterator, bool> inserted =
        data_.insert(std::make_pair(key, ownedValue));
    if (!inserted.second)
        throw ConflictError("key already exists");
}

// [Implementation 3-2] Read, erase, count, and sorted listing
// 조회 결과는 std::string으로 복사해 TextBuffer의 내부 포인터를 밖으로 내보내지 않습니다.
bool Store::get(const std::string &key, std::string &value) const {
    const std::map<std::string, TextBuffer>::const_iterator found = data_.find(key);
    if (found == data_.end())
        return false;
    value = found->second.c_str();
    return true;
}

bool Store::erase(const std::string &key) {
    return data_.erase(key) != 0;
}

std::size_t Store::size() const {
    return data_.size();
}

std::size_t Store::capacity() const {
    return capacity_;
}

std::vector<StoreEntry> Store::entries() const {
    std::vector<StoreEntry> result;
    result.reserve(data_.size());
    for (std::map<std::string, TextBuffer>::const_iterator it = data_.begin();
         it != data_.end(); ++it) {
        result.push_back(StoreEntry(it->first, it->second.c_str()));
    }
    return result;
}
