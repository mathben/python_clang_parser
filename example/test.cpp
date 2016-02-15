template<typename TData>
class Foo
{
public:
  typedef Foo Self;
  typedef TData Data;
  Foo();
  // just a comment
  Data getData(int i, char const* s);
  Data getVData(int i, char const* s);
private:
  /// my precious data
  Data m_data;
};

typedef Foo<int> IntFoo;

